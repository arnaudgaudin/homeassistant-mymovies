"""Config and options flows for the My Movies integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

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

from . import omdb, tmdb
from .api import MyMoviesAuthError, MyMoviesClient, MyMoviesError
from .catalog import CatalogEntry, CatalogStore, InvalidExportError, read_uploaded_export
from .const import CONF_EXPORT_FILE, CONF_OMDB_API_KEY, CONF_TMDB_API_KEY, DOMAIN, KEY_URLS, api_enabled

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
KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
# TMDB gives the covers, French titles, box sets and details: its key is required.
# OMDb (IMDb data) only completes what TMDB leaves empty: its key is optional.
KEYS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TMDB_API_KEY): KEY_SELECTOR,
        vol.Optional(CONF_OMDB_API_KEY): KEY_SELECTOR,
    }
)
OPTIONS_SCHEMA = vol.Schema(
    {vol.Optional(CONF_EXPORT_FILE): FileSelector(FileSelectorConfig(accept=".csv,text/csv"))}
).extend(KEYS_SCHEMA.schema)


async def _async_check_keys(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str]]:
    """Check the TMDB and OMDb keys; return the form errors and the options to keep."""
    session = async_get_clientsession(hass)
    errors: dict[str, str] = {}
    options = {}
    tmdb_key = (user_input.get(CONF_TMDB_API_KEY) or "").strip()
    try:
        await tmdb.async_validate_key(session, tmdb_key)
        options[CONF_TMDB_API_KEY] = tmdb_key
    except tmdb.TmdbAuthError:
        errors[CONF_TMDB_API_KEY] = "invalid_tmdb_key"
    except tmdb.TmdbError:
        errors["base"] = "tmdb_unreachable"
    if omdb_key := (user_input.get(CONF_OMDB_API_KEY) or "").strip():
        try:
            await omdb.async_validate_key(session, omdb_key)
            options[CONF_OMDB_API_KEY] = omdb_key
        except omdb.OmdbAuthError:
            errors[CONF_OMDB_API_KEY] = "invalid_omdb_key"
        except omdb.OmdbError:
            errors["base"] = "omdb_unreachable"
    return errors, options


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
        if not api_enabled():
            return await self.async_step_local()
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

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Without the API: one collection, filled from the CSV export after setup."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, options = await _async_check_keys(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="My Movies", data={}, options=options)
        return self.async_show_form(
            step_id="local",
            data_schema=self.add_suggested_values_to_schema(KEYS_SCHEMA, user_input),
            errors=errors,
            description_placeholders=KEY_URLS,
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


class MyMoviesOptionsFlow(OptionsFlow):
    """Import the collection export and set the TMDB and optional OMDb keys."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, options = await _async_check_keys(self.hass, user_input)
            if not errors and (file_id := user_input.get(CONF_EXPORT_FILE)):
                try:
                    catalog = await self.hass.async_add_executor_job(
                        read_uploaded_export, self.hass, file_id
                    )
                except InvalidExportError:
                    errors[CONF_EXPORT_FILE] = "invalid_export"
                else:
                    await self._async_save_catalog(catalog)
            if not errors:
                # Saving the options reloads the entry, which applies both changes.
                return self.async_create_entry(data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                {
                    CONF_TMDB_API_KEY: self.config_entry.options.get(CONF_TMDB_API_KEY, ""),
                    CONF_OMDB_API_KEY: self.config_entry.options.get(CONF_OMDB_API_KEY, ""),
                },
            ),
            errors=errors,
            description_placeholders={"count": str(len(self._store_catalog())), **KEY_URLS},
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
