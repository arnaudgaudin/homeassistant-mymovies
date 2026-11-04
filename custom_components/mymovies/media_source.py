"""Film wall: the collection as a media source with cover art.

The titles are physical discs, so they can be browsed but not played.
"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.http.auth import async_sign_path
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import MyMoviesConfigEntry

THUMBNAIL_URL_LIFETIME = timedelta(hours=24)


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Set up the My Movies media source."""
    return MyMoviesMediaSource(hass)


class MyMoviesMediaSource(MediaSource):
    """Browse the collection as a wall of covers."""

    name = "My Movies"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        raise Unresolvable("My Movies titles are physical discs and cannot be played")

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        entries: list[MyMoviesConfigEntry] = [
            e for e in self.hass.config_entries.async_entries(DOMAIN)
            if e.state is ConfigEntryState.LOADED
        ]
        if item.identifier:
            entry = next((e for e in entries if e.entry_id == item.identifier), None)
            if entry is None:
                raise Unresolvable(f"Unknown My Movies account {item.identifier}")
            return self._wall(entry)
        if len(entries) == 1:
            return self._wall(entries[0])
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MOVIE,
            title=self.name,
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.DIRECTORY,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=e.entry_id,
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.MOVIE,
                    title=e.title,
                    can_play=False,
                    can_expand=True,
                )
                for e in entries
            ],
        )

    def _wall(self, entry: MyMoviesConfigEntry) -> BrowseMediaSource:
        coordinator = entry.runtime_data
        children = []
        for title in coordinator.data.titles.values():
            info = coordinator.entry_for(title)
            name = info.title if info else f"#{title.collection_number}"
            if info and info.year:
                name = f"{name} ({info.year})"
            if title.watched:
                name = f"✓ {name}"
            thumbnail = coordinator.poster_url(title) or async_sign_path(
                self.hass,
                f"/api/mymovies/thumbnail/{entry.entry_id}/{title.id}",
                THUMBNAIL_URL_LIFETIME,
            )
            sort_key = (info.sort_title.casefold() if info else "~", title.collection_number)
            children.append(
                (
                    sort_key,
                    BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=f"{entry.entry_id}/{title.id}",
                        media_class=MediaClass.MOVIE,
                        media_content_type=MediaType.MOVIE,
                        title=name,
                        can_play=False,
                        can_expand=False,
                        thumbnail=thumbnail,
                    ),
                )
            )
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=entry.entry_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.MOVIE,
            title=f"{self.name} ({entry.title})",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.MOVIE,
            children=[child for _, child in sorted(children, key=lambda c: c[0])],
        )
