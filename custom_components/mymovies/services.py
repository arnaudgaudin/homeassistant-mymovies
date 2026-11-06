"""Services for the My Movies integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .api import BoxSetChild, CollectionTitle, MyMoviesError
from .catalog import normalize_title as _norm
from .const import ATTR_NOTES, ATTR_TITLE, DOMAIN, api_enabled
from .coordinator import MyMoviesConfigEntry

SERVICE_MARK_WATCHED = "mark_watched"
SERVICE_CLEAR_WATCHED = "clear_watched"
SERVICE_GET_TITLES = "get_titles"

_ACCOUNT = {vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string}
_BASE = {vol.Required(ATTR_TITLE): cv.string, **_ACCOUNT}
MARK_SCHEMA = vol.Schema({**_BASE, vol.Optional(ATTR_NOTES, default=""): cv.string})
CLEAR_SCHEMA = vol.Schema(_BASE)
GET_TITLES_SCHEMA = vol.Schema(_ACCOUNT)


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


def _resolve(entry: MyMoviesConfigEntry, ref: str) -> CollectionTitle | BoxSetChild:
    """Find a title or a box-set film by ID, collection number, IMDb ID or (original) title."""
    coordinator = entry.runtime_data
    titles = coordinator.data.titles
    # Films of box sets also owned as their own title are reached through that title.
    films = [
        (child, titles.get(parent))
        for parent, children in coordinator.data.box_sets.items()
        for child in children
        if child.id.lower() not in coordinator.data.child_titles
    ]
    ref = ref.strip()
    key = ref.lower()
    if match := titles.get(key):
        return match
    if match := next((child for child, _ in films if child.id.lower() == key), None):
        return match
    candidates: list[tuple[CollectionTitle | BoxSetChild, str]]
    if ref.isdigit():
        candidates = [
            (t, f"#{t.collection_number}") for t in titles.values() if t.collection_number == int(ref)
        ]
    elif key.startswith("tt"):
        candidates = [
            (t, f"#{t.collection_number}")
            for t in titles.values()
            if (info := coordinator.entry_for(t)) and info.imdb == key
        ]
    else:
        wanted = _norm(ref)
        candidates = [
            (t, f"#{t.collection_number}")
            for t in titles.values()
            if (info := coordinator.entry_for(t))
            and wanted in (_norm(info.title), _norm(info.original_title))
        ] + [
            (child, f"#{parent.collection_number if parent else '?'} › {child.title}")
            for child, parent in films
            if wanted in (_norm(child.title), _norm(child.original_title))
        ]
    if not candidates:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="title_not_found",
            translation_placeholders={"title": ref},
        )
    if len(candidates) > 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="title_ambiguous",
            translation_placeholders={
                "title": ref,
                "numbers": ", ".join(label for _, label in candidates),
            },
        )
    return candidates[0][0]


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register mark_watched, clear_watched and get_titles."""

    async def _write(call: ServiceCall, mark: bool) -> None:
        entry = _get_entry(hass, call)
        if entry.runtime_data.offline:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="offline")
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
        if isinstance(title, BoxSetChild):
            entry.runtime_data.set_child_watched(title.id, mark)
        await entry.runtime_data.async_request_refresh()

    async def mark_watched(call: ServiceCall) -> None:
        await _write(call, mark=True)

    async def clear_watched(call: ServiceCall) -> None:
        await _write(call, mark=False)

    async def get_titles(call: ServiceCall) -> ServiceResponse:
        coordinator = _get_entry(hass, call).runtime_data
        titles = sorted(coordinator.data.titles.values(), key=lambda t: t.collection_number)
        return {"titles": [coordinator.describe(t) for t in titles]}

    # Watched writes go through the My Movies API: not offered while it is switched off.
    if api_enabled():
        hass.services.async_register(DOMAIN, SERVICE_MARK_WATCHED, mark_watched, schema=MARK_SCHEMA)
        hass.services.async_register(DOMAIN, SERVICE_CLEAR_WATCHED, clear_watched, schema=CLEAR_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_TITLES,
        get_titles,
        schema=GET_TITLES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
