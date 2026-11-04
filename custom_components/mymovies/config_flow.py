"""Config and options flows for the My Movies integration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    FileSelector,
    FileSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import tmdb
from .api import MyMoviesAuthError, MyMoviesClient, MyMoviesError
from .catalog import CatalogEntry, CatalogStore, InvalidExportError, parse_export
from .const import CONF_EXPORT_FILE, CONF_TMDB_API_KEY, DOMAIN

PASSWORD_SELECTOR = TextSelector(
    TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
)
USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(TextSelectorConfig(autocomplete="username")),
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)
REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR})
OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_EXPORT_FILE): FileSelector(FileSelectorConfig(accept=".csv,text/csv")),
        vol.Optional(CONF_TMDB_API_KEY): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class MyMoviesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Sign in with a My Movies account."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MyMoviesOptionsFlow()

    async def _async_validate(self, data: Mapping[str, Any]) -> dict[str, str]:
        """Try the credentials against the API; return form errors."""
        client = MyMoviesClient(
            async_get_clientsession(self.hass), data[CONF_USERNAME], data[CONF_PASSWORD]
        )
        try:
            await client.async_get_titles()
        except MyMoviesAuthError:
            return {"base": "invalid_auth"}
        except MyMoviesError:
            return {"base": "cannot_connect"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the account credentials."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_USERNAME] = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            errors = await self._async_validate(user_input)
            if not errors:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(USER_SCHEMA, user_input),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Start re-authentication when the API rejects the stored password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            errors = await self._async_validate(data)
            if not errors:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )


def _read_export(hass: HomeAssistant, file_id: str) -> dict[int, CatalogEntry]:
    """Parse an uploaded export (runs in the executor)."""
    with process_uploaded_file(hass, file_id) as path:
        return parse_export(Path(path))


class MyMoviesOptionsFlow(OptionsFlow):
    """Import the collection export and set the optional TMDB key."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = (user_input.get(CONF_TMDB_API_KEY) or "").strip()
            if api_key:
                try:
                    await tmdb.async_validate_key(async_get_clientsession(self.hass), api_key)
                except tmdb.TmdbAuthError:
                    errors[CONF_TMDB_API_KEY] = "invalid_tmdb_key"
                except tmdb.TmdbError:
                    errors["base"] = "tmdb_unreachable"
            if not errors and (file_id := user_input.get(CONF_EXPORT_FILE)):
                try:
                    catalog = await self.hass.async_add_executor_job(
                        _read_export, self.hass, file_id
                    )
                except InvalidExportError:
                    errors[CONF_EXPORT_FILE] = "invalid_export"
                else:
                    await self._async_save_catalog(catalog)
            if not errors:
                # Saving the options reloads the entry, which applies both changes.
                return self.async_create_entry(
                    data={CONF_TMDB_API_KEY: api_key} if api_key else {}
                )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {CONF_TMDB_API_KEY: self.config_entry.options.get(CONF_TMDB_API_KEY, "")},
            ),
            errors=errors,
            description_placeholders={"count": str(len(self._store_catalog()))},
        )

    def _store_catalog(self) -> dict[int, CatalogEntry]:
        if self.config_entry.state is ConfigEntryState.LOADED:
            return self.config_entry.runtime_data.store.catalog
        return {}

    async def _async_save_catalog(self, catalog: dict[int, CatalogEntry]) -> None:
        """Save through the running store when loaded, so nothing overwrites it."""
        if self.config_entry.state is ConfigEntryState.LOADED:
            store = self.config_entry.runtime_data.store
        else:
            store = CatalogStore(self.hass, self.config_entry.entry_id)
            await store.async_load()
        store.catalog = catalog
        await store.async_save()
