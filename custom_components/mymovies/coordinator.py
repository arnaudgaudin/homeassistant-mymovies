"""Data update coordinator for the My Movies integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import tmdb
from .api import CollectionTitle, MyMoviesAuthError, MyMoviesClient, MyMoviesError
from .catalog import CatalogEntry, CatalogStore
from .const import CONF_TMDB_API_KEY, DOMAIN, TMDB_IMAGE_URL, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type MyMoviesConfigEntry = ConfigEntry[MyMoviesCoordinator]


@dataclass(slots=True)
class MyMoviesData:
    """Collection snapshot: titles keyed by their lower-case ID."""

    titles: dict[str, CollectionTitle]


class MyMoviesCoordinator(DataUpdateCoordinator[MyMoviesData]):
    """Poll the collection and its watched flags; hold the imported catalog."""

    config_entry: MyMoviesConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: MyMoviesConfigEntry,
        client: MyMoviesClient,
        store: CatalogStore,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.store = store
        self._thumbnails: dict[str, bytes | None] = {}

    async def _async_update_data(self) -> MyMoviesData:
        try:
            titles = await self.client.async_get_titles()
        except MyMoviesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MyMoviesError as err:
            raise UpdateFailed(str(err)) from err
        data = MyMoviesData(titles={t.id.lower(): t for t in titles})
        self._update_catalog_issue(data)
        return data

    def _update_catalog_issue(self, data: MyMoviesData) -> None:
        """Ask for a (new) export when titles have no name."""
        issue_id = f"catalog_{self.config_entry.entry_id}"
        missing = sum(t.collection_number not in self.store.catalog for t in data.titles.values())
        if not missing:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="catalog_outdated" if self.store.catalog else "catalog_missing",
            translation_placeholders={"account": self.config_entry.title, "count": str(missing)},
        )

    def entry_for(self, title: CollectionTitle) -> CatalogEntry | None:
        """Catalog data of a title, when the export knows it."""
        return self.store.catalog.get(title.collection_number)

    def poster_url(self, title: CollectionTitle) -> str | None:
        """TMDB poster URL of a title, when known."""
        entry = self.entry_for(title)
        path = self.store.posters.get(entry.imdb) if entry and entry.imdb else None
        return f"{TMDB_IMAGE_URL}{path}" if path else None

    def describe(self, title: CollectionTitle) -> dict[str, Any]:
        """Everything known about a title, for service responses."""
        entry = self.entry_for(title)
        return {
            "id": title.id,
            "collection_number": title.collection_number,
            "title": entry.title if entry else None,
            "original_title": entry.original_title if entry else None,
            "imdb": entry.imdb if entry else None,
            "year": entry.year if entry else None,
            "watched": title.watched,
            "poster": self.poster_url(title),
        }

    async def async_get_thumbnail(self, title_id: str) -> bytes | None:
        """My Movies cover thumbnail of a title of this collection (cached)."""
        key = title_id.lower()
        if key not in self.data.titles:
            return None
        if key not in self._thumbnails:
            self._thumbnails[key] = await self.client.async_get_thumbnail(self.data.titles[key].id)
        return self._thumbnails[key]

    async def async_fetch_posters(self) -> None:
        """Look up the TMDB posters not cached yet (needs a TMDB API key)."""
        api_key = self.config_entry.options.get(CONF_TMDB_API_KEY)
        if not api_key:
            return
        session = async_get_clientsession(self.hass)
        todo = sorted(
            {e.imdb for e in self.store.catalog.values() if e.imdb and e.imdb not in self.store.posters}
        )
        for imdb in todo:
            try:
                self.store.posters[imdb] = await tmdb.async_find_poster(session, api_key, imdb)
            except tmdb.TmdbError as err:
                _LOGGER.warning("TMDB poster lookup stopped at %s: %s", imdb, err)
                break
        if todo:
            await self.store.async_save()
            self.async_update_listeners()
