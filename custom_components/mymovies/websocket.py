"""WebSocket API feeding the My Movies panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http.auth import async_sign_path
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, THUMBNAIL_PATH, THUMBNAIL_URL_LIFETIME


@callback
def async_setup_websocket(hass: HomeAssistant) -> None:
    """Register the panel's commands."""
    websocket_api.async_register_command(hass, ws_collection)


@websocket_api.websocket_command(
    {vol.Required("type"): "mymovies/collection", vol.Optional("entry_id"): str}
)
@callback
def ws_collection(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send the collection with details, box sets and cover URLs."""
    entries = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED
    ]
    if entry_id := msg.get("entry_id"):
        entries = [e for e in entries if e.entry_id == entry_id]
    if not entries:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "No My Movies account is loaded")
        return
    entry = entries[0]
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
