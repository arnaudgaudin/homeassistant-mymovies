"""HTTP view serving the My Movies cover thumbnails of the user's titles."""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from pathlib import Path

from .api import MyMoviesError
from .const import DOMAIN
from .covers import covers_dir, valid_key


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


class MyMoviesCoverView(HomeAssistantView):
    """Serve a cover uploaded by the user for one of their titles."""

    url = "/api/mymovies/cover/{entry_id}/{key}"
    name = "api:mymovies:cover"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request, entry_id: str, key: str) -> web.StreamResponse:
        entry = self.hass.config_entries.async_get_entry(entry_id)
        if (
            entry is None
            or entry.domain != DOMAIN
            or entry.state is not ConfigEntryState.LOADED
            or not valid_key(key)
        ):
            raise web.HTTPNotFound
        override = entry.runtime_data.store.overrides.get(key) or {}
        if override.get("source") != "upload":
            raise web.HTTPNotFound
        path = covers_dir(self.hass) / Path(override["file"]).name
        if not await self.hass.async_add_executor_job(path.is_file):
            raise web.HTTPNotFound
        return web.FileResponse(path, headers={"Cache-Control": "private, max-age=3600"})
