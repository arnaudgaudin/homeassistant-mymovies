"""Services for the My Movies integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .api import CollectionTitle, MyMoviesError
from .const import ATTR_NOTES, ATTR_TITLE, DOMAIN
from .coordinator import MyMoviesConfigEntry

SERVICE_MARK_WATCHED = "mark_watched"
SERVICE_CLEAR_WATCHED = "clear_watched"

_BASE = {
    vol.Required(ATTR_TITLE): cv.string,
    vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
}
MARK_SCHEMA = vol.Schema({**_BASE, vol.Optional(ATTR_NOTES, default=""): cv.string})
CLEAR_SCHEMA = vol.Schema(_BASE)


def _get_entry(hass: HomeAssistant, call: ServiceCall) -> MyMoviesConfigEntry:
    """The loaded account to act on (config_entry_id needed when several)."""
    entries = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
    ]
    if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
        entries = [e for e in entries if e.entry_id == entry_id]
    if not entries:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_entry")
    if len(entries) > 1:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="several_entries")
    return entries[0]


def _resolve(entry: MyMoviesConfigEntry, ref: str) -> CollectionTitle:
    """Find a title by its ID or its collection number."""
    ref = ref.strip()
    titles = entry.runtime_data.data.titles
    match = titles.get(ref.lower())
    if match is None and ref.isdigit():
        match = next((t for t in titles.values() if t.collection_number == int(ref)), None)
    if match is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="title_not_found",
            translation_placeholders={"title": ref},
        )
    return match


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register mark_watched and clear_watched."""

    async def _write(call: ServiceCall, mark: bool) -> None:
        entry = _get_entry(hass, call)
        title = _resolve(entry, call.data[ATTR_TITLE])
        client = entry.runtime_data.client
        try:
            if mark:
                await client.async_mark_watched(title.id, dt_util.now(), call.data[ATTR_NOTES])
            else:
                await client.async_clear_watched(title.id)
        except MyMoviesError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"error": str(err)},
            ) from err
        await entry.runtime_data.async_request_refresh()

    async def mark_watched(call: ServiceCall) -> None:
        await _write(call, mark=True)

    async def clear_watched(call: ServiceCall) -> None:
        await _write(call, mark=False)

    hass.services.async_register(DOMAIN, SERVICE_MARK_WATCHED, mark_watched, schema=MARK_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_WATCHED, clear_watched, schema=CLEAR_SCHEMA)
