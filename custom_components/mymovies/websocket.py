"""WebSocket API feeding the My Movies panel."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import tmdb
from .catalog import InvalidExportError, read_uploaded_export
from .const import CONF_TMDB_API_KEY, DOMAIN, THUMBNAIL_URL_LIFETIME, TMDB_IMAGE_URL, api_enabled
from .coordinator import MyMoviesConfigEntry
from .covers import InvalidImageError, read_upload, remove_upload, save_upload, valid_key

_TMDB_PATH = re.compile(r"^/[A-Za-z0-9_-]+\.(jpg|jpeg|png)$")


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the panel's commands."""
    websocket_api.async_register_command(hass, ws_collection)
    websocket_api.async_register_command(hass, ws_import_export)
    websocket_api.async_register_command(hass, ws_cover_choices)
    websocket_api.async_register_command(hass, ws_set_cover)


def _sign(hass: HomeAssistant, connection: websocket_api.ActiveConnection, path: str) -> str:
    return async_sign_path(
        hass, path, THUMBNAIL_URL_LIFETIME, refresh_token_id=connection.refresh_token_id
    )


def _finish(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, item: dict[str, Any]
) -> dict[str, Any]:
    """Turn covers served by Home Assistant into URLs signed for this viewer."""
    for target in (item, *item.get("children", [])):
        if path := target.pop("_sign", None):
            target["poster"] = _sign(hass, connection, path)
    return item


def _loaded_entry(hass: HomeAssistant, entry_id: str | None) -> MyMoviesConfigEntry | None:
    """The requested loaded account, or the first one."""
    entries = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
    ]
    if entry_id:
        entries = [e for e in entries if e.entry_id == entry_id]
    return entries[0] if entries else None


@websocket_api.websocket_command(
    {vol.Required("type"): "mymovies/collection", vol.Optional("entry_id"): str}
)
@callback
def ws_collection(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send the collection with details, box sets and cover URLs."""
    entry = _loaded_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "No My Movies account is loaded")
        return
    coordinator = entry.runtime_data
    titles = [
        _finish(hass, connection, coordinator.describe(title, details=True))
        for title in coordinator.data.titles.values()
    ]
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "account": entry.title,
            "titles": titles,
            "api": api_enabled() and not coordinator.offline,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mymovies/import_export",
        vol.Required("file_id"): str,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_import_export(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Import a collection export uploaded from the panel (admins only)."""
    entry = _loaded_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "No My Movies account is loaded")
        return
    try:
        catalog = await hass.async_add_executor_job(read_uploaded_export, hass, msg["file_id"])
    except (InvalidExportError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_export", str(err))
        return
    await entry.runtime_data.async_import_catalog(catalog)
    connection.send_result(msg["id"], {"count": len(catalog)})


def _known(entry: MyMoviesConfigEntry, key: str) -> bool:
    coordinator = entry.runtime_data
    return valid_key(key) and (key in coordinator.data.titles or coordinator.find_child(key) is not None)


@websocket_api.websocket_command(
    {vol.Required("type"): "mymovies/cover_choices", vol.Required("title_id"): str, vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_cover_choices(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Covers a title can use: every TMDB poster (best first) and the My Movies one."""
    entry = _loaded_entry(hass, msg.get("entry_id"))
    key = msg["title_id"].lower()
    if entry is None or not _known(entry, key):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unknown title")
        return
    coordinator = entry.runtime_data
    found = coordinator.store.covers.get(key) or {}
    api_key = entry.options.get(CONF_TMDB_API_KEY)
    choices: list[dict[str, Any]] = []
    error = None
    if api_key and found.get("kind"):
        match = tmdb.TmdbMatch(found["kind"], found["id"], season=found.get("season"))
        lang = coordinator.language()
        try:
            posters = await tmdb.async_posters(async_get_clientsession(hass), api_key, match, lang)
        except tmdb.TmdbError as err:
            posters, error = [], str(err)
        choices += [
            {"source": "tmdb", "url": f"{TMDB_IMAGE_URL}{p['path']}", **p}
            for p in tmdb.rank_posters(posters, lang)
        ]
    if mymovies := coordinator.mymovies_cover(key):
        url = mymovies.get("url") or _sign(hass, connection, mymovies["sign"])
        choices.append({"source": "mymovies", "url": url, "width": mymovies["width"], "height": mymovies["height"]})
    override = coordinator.store.overrides.get(key) or {}
    current = override or ({"source": "tmdb", "path": found["path"]} if found.get("path") else {})
    connection.send_result(
        msg["id"],
        {
            "choices": choices,
            "chosen": bool(override),
            "current": {"source": current.get("source"), "path": current.get("path")},
            "tmdb_known": bool(found.get("kind")),
            "tmdb_key": bool(api_key),
            "error": error,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "mymovies/set_cover",
        vol.Required("title_id"): str,
        vol.Required("source"): vol.In(["auto", "tmdb", "mymovies", "upload"]),
        vol.Optional("path"): str,
        vol.Optional("width"): int,
        vol.Optional("height"): int,
        vol.Optional("file_id"): str,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_set_cover(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Choose the cover of a title: automatic, a TMDB poster, My Movies or an uploaded image."""
    entry = _loaded_entry(hass, msg.get("entry_id"))
    key = msg["title_id"].lower()
    if entry is None or not _known(entry, key):
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unknown title")
        return
    store = entry.runtime_data.store
    previous = store.overrides.get(key) or {}
    source = msg["source"]
    if source == "auto":
        store.overrides.pop(key, None)
    elif source == "tmdb":
        if not _TMDB_PATH.match(msg.get("path", "")):
            connection.send_error(msg["id"], "invalid_format", "Invalid TMDB poster")
            return
        store.overrides[key] = {
            "source": "tmdb",
            "path": msg["path"],
            "width": msg.get("width", 0),
            "height": msg.get("height", 0),
        }
    elif source == "mymovies":
        store.overrides[key] = {"source": "mymovies"}
    else:
        try:
            data = await hass.async_add_executor_job(read_upload, hass, msg.get("file_id", ""))
            store.overrides[key] = await hass.async_add_executor_job(
                save_upload, hass, entry.entry_id, key, data
            )
        except (InvalidImageError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_image", str(err))
            return
    if previous.get("source") == "upload" and store.overrides.get(key, {}).get("file") != previous.get("file"):
        await hass.async_add_executor_job(remove_upload, hass, previous["file"])
    await store.async_save()
    entry.runtime_data.async_update_listeners()
    connection.send_result(msg["id"], {})
