"""HTTP view serving the My Movies cover thumbnails of the user's titles."""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .api import MyMoviesError
from .const import DOMAIN


class MyMoviesThumbnailView(HomeAssistantView):
    """Proxy a thumbnail; only titles of a loaded account's collection are served."""

    url = "/api/mymovies/thumbnail/{entry_id}/{title_id}"
    name = "api:mymovies:thumbnail"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str, title_id: str) -> web.Response:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
            raise web.HTTPNotFound
        try:
            image = await entry.runtime_data.async_get_thumbnail(title_id)
        except MyMoviesError as err:
            raise web.HTTPBadGateway from err
        if image is None:
            raise web.HTTPNotFound
        return web.Response(
            body=image,
            content_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=86400"},
        )
