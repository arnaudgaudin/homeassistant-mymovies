"""Data update coordinator for the My Movies integration."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import tmdb
from .api import (
    BoxSetChild,
    CollectionTitle,
    MyMoviesAuthError,
    MyMoviesClient,
    MyMoviesError,
)
from .catalog import CatalogEntry, CatalogStore
from .const import CONF_TMDB_API_KEY, DOMAIN, TMDB_IMAGE_URL, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

# The API gives the watched flag of box-set films one by one: read them less often.
CHILDREN_WATCHED_INTERVAL = timedelta(hours=6)

type MyMoviesConfigEntry = ConfigEntry[MyMoviesCoordinator]

DETAIL_FIELDS = (
    "sort_title", "runtime", "rating", "personal_rating", "parental_rating", "release_date",
    "added", "disc_type", "media_type", "group", "edition", "genres", "director", "actors",
    "description",
)


@dataclass(slots=True)
class MyMoviesData:
    """Collection snapshot."""

    titles: dict[str, CollectionTitle]  # by lower-case title ID
    box_sets: dict[str, list[BoxSetChild]]  # films of each box set, by lower-case box set ID
    children_watched: dict[str, bool] = field(default_factory=dict)  # by lower-case film ID


class MyMoviesCoordinator(DataUpdateCoordinator[MyMoviesData]):
    """Poll the collection, its watched flags and box sets; hold the imported catalog."""

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
        self._fetching = False
        self._box_set_cache: dict[str, list[BoxSetChild]] = {}
        self._children_watched: dict[str, bool] = {}
        self._children_checked: datetime | None = None

    async def _async_update_data(self) -> MyMoviesData:
        try:
            titles, box_sets = await asyncio.gather(
                self.client.async_get_titles(), self.client.async_get_box_set_children()
            )
        except MyMoviesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MyMoviesError as err:
            raise UpdateFailed(str(err)) from err
        by_id = {t.id.lower(): t for t in titles}
        await self._async_complete_box_sets(by_id, box_sets)
        await self._async_update_children_watched(box_sets)
        data = MyMoviesData(
            titles=by_id, box_sets=box_sets, children_watched=dict(self._children_watched)
        )
        self._update_catalog_issue(data)
        if self._tmdb_missing(data):
            self.config_entry.async_create_background_task(
                self.hass, self.async_fetch_tmdb(data), f"{DOMAIN}_tmdb_{self.config_entry.entry_id}"
            )
        return data

    async def _async_complete_box_sets(
        self, titles: dict[str, CollectionTitle], box_sets: dict[str, list[BoxSetChild]]
    ) -> None:
        """Add the films of box sets the user did not list, from the catalog.

        GetBoxSetChildTitlesForUser only returns box sets whose films the user listed;
        the others are read once per box set (titles without IMDb ID) and cached.
        """
        for key, title in titles.items():
            entry = self.entry_for(title)
            if not entry or entry.imdb or key in box_sets:
                continue
            if key not in self._box_set_cache:
                try:
                    self._box_set_cache[key] = await self.client.async_get_titles_in_box_set(title.id)
                except MyMoviesError as err:
                    _LOGGER.debug("Box set %s not readable: %s", title.id, err)
                    continue
            if self._box_set_cache[key]:
                box_sets[key] = self._box_set_cache[key]

    async def _async_update_children_watched(
        self, box_sets: dict[str, list[BoxSetChild]]
    ) -> None:
        """Read the watched flag of box-set films: all every few hours, new ones at once."""
        ids = {c.id.lower(): c.id for children in box_sets.values() for c in children}
        now = dt_util.utcnow()
        due = self._children_checked is None or now - self._children_checked >= CHILDREN_WATCHED_INTERVAL
        todo = list(ids) if due else [key for key in ids if key not in self._children_watched]
        if not todo:
            return
        limit = asyncio.Semaphore(4)

        async def read(key: str) -> None:
            async with limit:
                try:
                    self._children_watched[key] = await self.client.async_get_watched(ids[key])
                except MyMoviesError as err:
                    _LOGGER.debug("Watched flag of %s not readable: %s", ids[key], err)

        await asyncio.gather(*(read(key) for key in todo))
        if due:
            self._children_checked = now

    def set_child_watched(self, child_id: str, watched: bool) -> None:
        """Record a watched change made from Home Assistant on a box-set film."""
        self._children_watched[child_id.lower()] = watched
        if self.data:
            self.data.children_watched[child_id.lower()] = watched

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

    def _missing_imdb(self) -> list[str]:
        return sorted(
            {e.imdb for e in self.store.catalog.values() if e.imdb and e.imdb not in self.store.posters}
        )

    def _missing_children(self, data: MyMoviesData) -> list[BoxSetChild]:
        return [
            child
            for children in data.box_sets.values()
            for child in children
            if child.id not in self.store.children
        ]

    def _missing_box_posters(self, data: MyMoviesData) -> list[CollectionTitle]:
        """Titles without IMDb ID (box sets) whose TMDB collection was not looked up."""
        return [
            t
            for key, t in data.titles.items()
            if (entry := self.entry_for(t)) and not entry.imdb and key not in self.store.box_posters
        ]

    def _tmdb_missing(self, data: MyMoviesData) -> bool:
        return bool(self.config_entry.options.get(CONF_TMDB_API_KEY)) and bool(
            self._missing_imdb() or self._missing_children(data) or self._missing_box_posters(data)
        )

    async def async_fetch_tmdb(self, data: MyMoviesData) -> None:
        """Look up the TMDB posters and box-set films not cached yet."""
        api_key = self.config_entry.options.get(CONF_TMDB_API_KEY)
        if not api_key or self._fetching:
            return
        self._fetching = True
        session = async_get_clientsession(self.hass)
        changed = False
        try:
            for imdb in self._missing_imdb():
                self.store.posters[imdb] = await tmdb.async_find_poster(session, api_key, imdb)
                changed = True
            for child in self._missing_children(data):
                self.store.children[child.id] = await tmdb.async_search_movie(
                    session,
                    api_key,
                    child.original_title or child.title,
                    child.year,
                    self.hass.config.language,
                )
                changed = True
            for title in self._missing_box_posters(data):
                entry = self.entry_for(title)
                self.store.box_posters[title.id.lower()] = await tmdb.async_search_collection(
                    session, api_key, entry.title if entry else "", self.hass.config.language
                )
                changed = True
        except tmdb.TmdbError as err:
            _LOGGER.warning("TMDB lookups stopped: %s", err)
        finally:
            self._fetching = False
            if changed:
                await self.store.async_save()
                self.async_update_listeners()

    def entry_for(self, title: CollectionTitle) -> CatalogEntry | None:
        """Catalog data of a title, when the export knows it."""
        return self.store.catalog.get(title.collection_number)

    def poster_url(self, title: CollectionTitle) -> str | None:
        """Best TMDB poster of a title: its own, its box set's collection, or its first film's."""
        entry = self.entry_for(title)
        if entry and entry.imdb:
            path = self.store.posters.get(entry.imdb)
        else:
            path = self.store.box_posters.get(title.id.lower())
            if not path and self.data:
                path = next(
                    (
                        found["poster"]
                        for child in self.data.box_sets.get(title.id.lower(), [])
                        if (found := self.store.children.get(child.id, {})).get("poster")
                    ),
                    None,
                )
        return f"{TMDB_IMAGE_URL}{path}" if path else None

    def describe_child(self, child: BoxSetChild) -> dict[str, Any]:
        """One film of a box set, for the panel."""
        found = self.store.children.get(child.id, {})
        poster = f"{TMDB_IMAGE_URL}{found['poster']}" if found.get("poster") else child.thumbnail
        return {
            "id": child.id,
            "title": child.title,
            "original_title": child.original_title,
            "year": child.year,
            "edition": child.edition,
            "disc_type": child.disc_type,
            "poster": poster or None,
            "description": found.get("overview", ""),
            "watched": self.data.children_watched.get(child.id.lower(), False) if self.data else False,
        }

    def describe(self, title: CollectionTitle, *, details: bool = False) -> dict[str, Any]:
        """Everything known about a title (details: also the export columns and box set)."""
        entry = self.entry_for(title)
        data: dict[str, Any] = {
            "id": title.id,
            "collection_number": title.collection_number,
            "title": entry.title if entry else None,
            "original_title": entry.original_title if entry else None,
            "imdb": entry.imdb if entry else None,
            "year": entry.year if entry else None,
            "watched": title.watched,
            "poster": self.poster_url(title),
        }
        children = self.data.box_sets.get(title.id.lower(), []) if self.data else []
        if details:
            default = CatalogEntry("", "", "", None, None)
            for name in DETAIL_FIELDS:
                data[name] = getattr(entry or default, name)
            data["children"] = [self.describe_child(c) for c in children]
        elif children:
            keep = ("id", "title", "original_title", "year", "watched")
            data["children"] = [
                {k: v for k, v in self.describe_child(c).items() if k in keep} for c in children
            ]
        return data

    async def async_get_thumbnail(self, title_id: str) -> bytes | None:
        """My Movies cover thumbnail of a title of this collection (cached)."""
        key = title_id.lower()
        if key not in self.data.titles:
            return None
        if key not in self._thumbnails:
            self._thumbnails[key] = await self.client.async_get_thumbnail(self.data.titles[key].id)
        return self._thumbnails[key]
