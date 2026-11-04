"""WebSocket API feeding the My Movies panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .catalog import InvalidExportError, read_uploaded_export
from .const import DOMAIN, THUMBNAIL_PATH, THUMBNAIL_URL_LIFETIME
from .coordinator import MyMoviesConfigEntry


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the panel's commands."""
    websocket_api.async_register_command(hass, ws_collection)
    websocket_api.async_register_command(hass, ws_import_export)


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
    titles = []
    for title in coordinator.data.titles.values():
        item = coordinator.describe(title, details=True)
        if not item["poster"]:
            item["poster"] = async_sign_path(
                hass,
                THUMBNAIL_PATH.format(entry_id=entry.entry_id, title_id=title.id),
                THUMBNAIL_URL_LIFETIME,
                refresh_token_id=connection.refresh_token_id,
            )
        titles.append(item)
    connection.send_result(
        msg["id"], {"entry_id": entry.entry_id, "account": entry.title, "titles": titles}
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
