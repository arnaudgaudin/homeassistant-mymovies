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

from . import omdb, tmdb
from .api import (
    BoxSetChild,
    CollectionTitle,
    MyMoviesAuthError,
    MyMoviesClient,
    MyMoviesError,
)
from .catalog import IMPORT_UPDATE, CatalogEntry, CatalogStore, normalize_title, title_id
from .covers import remove_upload
from .const import (
    CONF_OMDB_API_KEY,
    CONF_TMDB_API_KEY,
    COVER_PATH,
    DOMAIN,
    MYMOVIES_THUMBNAIL,
    THUMBNAIL_PATH,
    TMDB_IMAGE_URL,
    UPDATE_INTERVAL,
    api_enabled,
)

_LOGGER = logging.getLogger(__name__)

# Bumped when what is kept from TMDB changes, so that every title is looked up again once.
LOOKUP_VERSION = 6

# The API gives the watched flag of box-set films one by one: read them less often.
CHILDREN_WATCHED_INTERVAL = timedelta(hours=6)

type MyMoviesConfigEntry = ConfigEntry[MyMoviesCoordinator]

DETAIL_FIELDS = (
    "sort_title", "runtime", "rating", "personal_rating", "parental_rating", "release_date",
    "added", "disc_type", "three_d", "media_type", "group", "edition", "genres", "director", "actors",
    "description",
)


@dataclass(slots=True)
class MyMoviesData:
    """Collection snapshot."""

    titles: dict[str, CollectionTitle]  # by lower-case title ID
    box_sets: dict[str, list[BoxSetChild]]  # films of each box set, by lower-case box set ID
    children_watched: dict[str, bool] = field(default_factory=dict)  # by lower-case film ID
    # Discs of a box set scanned as their own titles: film ID -> title ID, title ID -> box set ID.
    child_titles: dict[str, str] = field(default_factory=dict)
    box_of: dict[str, str] = field(default_factory=dict)


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
        # True when My Movies refuses its API: the collection comes from the export only.
        self.offline = False

    async def _async_update_data(self) -> MyMoviesData:
        if not api_enabled():
            return self._offline_data()
        # The titles first: a refusal there means My Movies closed its API.
        try:
            titles = await self.client.async_get_titles()
        except MyMoviesAuthError as err:
            if not self.store.catalog:
                raise ConfigEntryAuthFailed(str(err)) from err
            # My Movies closed its API to third-party apps: keep working from the export.
            if not self.offline:
                _LOGGER.warning("My Movies refuses API access (%s): using the imported export", err)
            return self._offline_data()
        except MyMoviesError as err:
            raise UpdateFailed(str(err)) from err
        self.offline = False
        try:
            box_sets = await self.client.async_get_box_set_children()
        except MyMoviesError as err:
            _LOGGER.warning("Box sets not readable from My Movies: %s", err)
            box_sets = {}
        by_id = {t.id.lower(): t for t in titles}
        await self._async_complete_box_sets(by_id, box_sets)
        data = MyMoviesData(titles=by_id, box_sets=box_sets)
        self._link_box_set_discs(data)
        await self._async_update_children_watched(data)
        data.children_watched = dict(self._children_watched)
        self._update_catalog_issue(data)
        if self._tmdb_missing(data):
            self.config_entry.async_create_background_task(
                self.hass, self.async_fetch_tmdb(data), f"{DOMAIN}_tmdb_{self.config_entry.entry_id}"
            )
        return data

    def _offline_data(self) -> MyMoviesData:
        """The collection as imported from the export, with a stable ID per title."""
        self.offline = True
        titles = {}
        for number, entry in self.store.catalog.items():
            key = title_id(number)
            titles[key] = CollectionTitle(
                id=key,
                collection_number=number,
                watched=self.local_watched(key, entry.watched),
                group=entry.group,
                added=entry.added,
                data_changed="",
                covers_changed="",
            )
        data = MyMoviesData(titles=titles, box_sets={})
        self._offline_box_sets(data)
        self._update_catalog_issue(data)
        if self._tmdb_missing(data):
            self.config_entry.async_create_background_task(
                self.hass, self.async_fetch_tmdb(data), f"{DOMAIN}_tmdb_{self.config_entry.entry_id}"
            )
        return data

    def _offline_box_sets(self, data: MyMoviesData) -> None:
        """Box sets from the export (discs owned as titles), else from TMDB collections."""
        by_number = {t.collection_number: t for t in data.titles.values()}
        discs = sorted(
            (e.box_order or 0, number, e) for number, e in self.store.catalog.items() if e.box in by_number
        )
        for _, number, entry in discs:
            box_key = by_number[entry.box].id.lower()
            disc = by_number[number]
            data.box_sets.setdefault(box_key, []).append(
                BoxSetChild(
                    id=disc.id,
                    parent_id=box_key,
                    title=entry.title,
                    original_title=entry.original_title,
                    year=entry.year,
                    edition=entry.edition,
                    disc_type=entry.disc_type,
                    thumbnail="",
                )
            )
            data.child_titles[disc.id.lower()] = disc.id.lower()
            data.box_of[disc.id.lower()] = box_key
        for key, title in data.titles.items():
            entry = self.entry_for(title)
            parts = (self.store.covers.get(key) or {}).get("parts") or []
            if key in data.box_sets or not entry or entry.imdb or not parts:
                continue
            # Only the films released before the box set (a later sequel is not in it).
            films = [
                p for p in parts if p["year"] and (not entry.release_date or p["release_date"] <= entry.release_date)
            ]
            # A premiere can predate the box set by a day (Jurassic World Rebirth): the
            # title's film count ("Trilogie", "5 Films") keeps the oldest ones.
            size = tmdb.box_set_size(entry.title) or tmdb.box_set_size(entry.original_title)
            if size:
                films = films[:size]
            for part in films:
                child_key = f"00000000-0000-0000-0001-{part['id']:012d}"
                self.store.covers[child_key] = (
                    {
                        "kind": "movie",
                        "id": part["id"],
                        "path": part["poster"] or None,
                        "width": 0,
                        "height": 0,
                        "overview": part["overview"],
                        "release_date": part["release_date"],
                        "genres": tmdb.genre_names(part.get("genre_ids") or []),
                        "rating": part.get("rating"),
                    }
                )
                data.box_sets.setdefault(key, []).append(
                    BoxSetChild(
                        id=child_key,
                        parent_id=key,
                        title=part["title"],
                        original_title=part["original_title"],
                        year=part["year"],
                        edition="",
                        disc_type=entry.disc_type,
                        thumbnail="",
                    )
                )

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

    def _link_box_set_discs(self, data: MyMoviesData) -> None:
        """Find the titles that are the discs of a box set, scanned on their own.

        Matched on (original) title and year; when several titles match (the same film
        owned twice), the one numbered closest after the box set is its disc.
        """
        used: set[str] = set()
        for box_key, children in data.box_sets.items():
            box = data.titles.get(box_key)
            if box is None:
                continue
            for child in children:
                names = {normalize_title(child.title), normalize_title(child.original_title)} - {""}
                candidates = []
                for key, title in data.titles.items():
                    info = self.entry_for(title)
                    if key in used or key in data.box_sets or info is None:
                        continue
                    if not names & {normalize_title(info.title), normalize_title(info.original_title)}:
                        continue
                    if child.year and info.year and child.year != info.year:
                        continue
                    candidates.append(title)
                if not candidates:
                    continue
                disc = min(
                    candidates,
                    key=lambda t: (
                        t.collection_number < box.collection_number,
                        abs(t.collection_number - box.collection_number),
                    ),
                )
                used.add(disc.id.lower())
                data.child_titles[child.id.lower()] = disc.id.lower()
                data.box_of[disc.id.lower()] = box_key

    async def _async_update_children_watched(self, data: MyMoviesData) -> None:
        """Read the watched flag of box-set films without their own title.

        All of them every few hours, new ones at once.
        """
        ids = {
            c.id.lower(): c.id
            for children in data.box_sets.values()
            for c in children
            if c.id.lower() not in data.child_titles
        }
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

    async def async_import_catalog(
        self, catalog: dict[int, CatalogEntry], mode: str = IMPORT_UPDATE
    ) -> dict[str, Any]:
        """Take a new export (update or full replace) and refresh what depends on it."""
        result = self.store.apply_import(catalog, mode)
        for name in result.pop("removed_files"):
            await self.hass.async_add_executor_job(remove_upload, self.hass, name)
        await self.store.async_save()
        await self.async_refresh()
        return result

    def local_watched(self, key: str, default: bool) -> bool:
        """Watched state kept in Home Assistant, else the export's."""
        viewing = self.store.viewings.get(key.lower())
        return viewing["watched"] if viewing else default

    async def async_log_viewing(self, key: str, watched: bool, when: datetime) -> None:
        """Without the API: log a viewing (dated, like My Movies) or clear them all."""
        key = key.lower()
        if watched:
            viewing = self.store.viewings.setdefault(key, {"watched": True, "dates": []})
            viewing["watched"] = True
            viewing["dates"].append(when.isoformat(timespec="seconds"))
        else:
            self.store.viewings[key] = {"watched": False, "dates": []}
        await self.store.async_save()
        self.async_set_updated_data(self._offline_data())

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

    # ---- TMDB lookups and covers -------------------------------------------

    def language(self) -> str:
        return (self.hass.config.language or "en")[:2]

    def _tmdb_todo(self, data: MyMoviesData) -> list[tuple[str, CollectionTitle | BoxSetChild]]:
        """Titles and box-set films without their own title, not looked up on TMDB yet."""
        todo: list[tuple[str, CollectionTitle | BoxSetChild]] = [
            (key, title)
            for key, title in data.titles.items()
            if self.entry_for(title) and (self.store.covers.get(key) or {}).get("v") != LOOKUP_VERSION
        ]
        todo += [
            (child.id.lower(), child)
            for children in data.box_sets.values()
            for child in children
            if child.id.lower() not in data.child_titles
            and (self.store.covers.get(child.id.lower()) or {}).get("v") != LOOKUP_VERSION
            and not child.id.startswith("00000000-0000-0000-0001-")  # TMDB collection films
        ]
        return todo

    def _omdb(self, key: str) -> dict[str, Any]:
        """What OMDb gave for a title or film ({} when not asked or unknown)."""
        return (self.store.covers.get(key) or {}).get("omdb") or {}

    def _omdb_todo(self, data: MyMoviesData) -> list[tuple[str, dict[str, Any]]]:
        """Films and series still missing a rating, genres or countries after TMDB.

        Each is asked once to OMDb (by IMDb ID, else by title and year); box sets are
        left out: their films complete them.
        """
        if not self.config_entry.options.get(CONF_OMDB_API_KEY):
            return []
        todo = []
        items: list[tuple[str, CatalogEntry | BoxSetChild]] = [
            (key, entry) for key, title in data.titles.items() if (entry := self.entry_for(title))
        ] + [(child.id.lower(), child) for children in data.box_sets.values() for child in children]
        for key, item in items:
            cover = self.store.covers.get(key)
            if cover is None or "omdb" in cover or key in data.box_sets or cover.get("kind") == "collection":
                continue
            entry = item if isinstance(item, CatalogEntry) else None
            if (entry and entry.rating) or cover.get("rating"):
                if ((entry and entry.genres) or cover.get("genres")) and cover.get("countries"):
                    continue
            todo.append((key, {
                "imdb": entry.imdb if entry else None,
                "title": item.original_title or item.title,
                "year": item.year,
            }))
        return todo

    def _tmdb_missing(self, data: MyMoviesData) -> bool:
        return bool(self.config_entry.options.get(CONF_TMDB_API_KEY)) and bool(
            self._tmdb_todo(data) or self._omdb_todo(data)
        )

    async def _async_fetch_omdb(self, session: Any, data: MyMoviesData) -> int:
        """Complete from OMDb what TMDB left empty; return how many titles were asked."""
        api_key = self.config_entry.options.get(CONF_OMDB_API_KEY)
        done = 0
        try:
            for key, query in self._omdb_todo(data):
                self.store.covers[key]["omdb"] = await omdb.async_lookup(session, api_key, **query)
                done += 1
        except omdb.OmdbAuthError as err:
            _LOGGER.warning("OMDb lookups stopped (key refused or daily limit reached): %s", err)
        except omdb.OmdbError as err:
            _LOGGER.warning("OMDb lookups stopped: %s", err)
        return done

    async def _async_season_at_release(
        self,
        session: Any,
        api_key: str,
        match: tmdb.TmdbMatch,
        item: CollectionTitle | BoxSetChild,
        lang: str,
    ) -> int | None:
        """Season of a series disc that names none: the last one aired when the disc came out.

        "Bref: L'intégrale" (2012) holds season 1; the series poster now shows the 2025
        season 2.
        """
        entry = self.entry_for(item) if isinstance(item, CollectionTitle) else None
        if not entry or not entry.release_date:
            return None
        seasons = await tmdb.async_tv_seasons(session, api_key, match.id, lang)
        aired = [s["season"] for s in seasons if s["air_date"] and s["air_date"] <= entry.release_date]
        return max(aired) if aired and len(aired) < len(seasons) else None

    async def _async_box_set_films(
        self, session: Any, api_key: str, match: tmdb.TmdbMatch, title: CollectionTitle, lang: str
    ) -> list[dict[str, Any]]:
        """Films of a box set's TMDB collection.

        A collection named after the franchise can be empty ("Collection Jurassic
        World"): then the films are taken from the collection of the franchise's
        film (the Jurassic Park saga), keeping those named after the franchise.
        """
        parts = await tmdb.async_collection_parts(session, api_key, match.id, lang)
        entry = self.entry_for(title)
        if parts or not entry:
            return parts
        franchise = tmdb.franchise_name(entry.title)
        collection_id = await tmdb.async_movie_collection(session, api_key, franchise, lang)
        if collection_id is None:
            return []
        wanted = normalize_title(franchise)
        return [
            p
            for p in await tmdb.async_collection_parts(session, api_key, collection_id, lang)
            if normalize_title(p["title"]).startswith(wanted)
            or normalize_title(p["original_title"]).startswith(wanted)
        ]

    @staticmethod
    def _looks_like_box_set(entry: CatalogEntry) -> bool:
        """No IMDb ID and a box-set word in the title ("Trilogie", "Intégrale 5 Films"...)."""
        return not entry.imdb and normalize_title(tmdb.franchise_name(entry.title)) != normalize_title(entry.title)

    async def _async_match(
        self,
        session: Any,
        api_key: str,
        key: str,
        item: CollectionTitle | BoxSetChild,
        data: MyMoviesData,
    ) -> tmdb.TmdbMatch | None:
        """Find a title on TMDB: by IMDb ID, as a collection (box set) or by title and year."""
        lang = self.language()
        if isinstance(item, BoxSetChild):
            return await tmdb.async_search_movie(
                session, api_key, item.original_title or item.title, item.year, lang
            )
        entry = self.entry_for(item)
        if key in data.box_sets or self._looks_like_box_set(entry):
            return await tmdb.async_search_collection(session, api_key, entry.title, lang)
        if entry.imdb:
            match = await tmdb.async_find_imdb(session, api_key, entry.imdb, lang)
            if match and match.kind == "tv":
                # One IMDb ID for the whole series: each season disc gets its season's poster.
                match.season = tmdb.season_number(entry.title) or tmdb.season_number(entry.original_title)
            return match
        match = await tmdb.async_search_movie(session, api_key, entry.original_title, entry.year, lang)
        if match is None and entry.title != entry.original_title:
            match = await tmdb.async_search_movie(session, api_key, entry.title, entry.year, lang)
        return match

    async def async_fetch_tmdb(self, data: MyMoviesData) -> None:
        """Find every title on TMDB once and keep its best poster with its size."""
        api_key = self.config_entry.options.get(CONF_TMDB_API_KEY)
        if not api_key or self._fetching:
            return
        self._fetching = True
        session = async_get_clientsession(self.hass)
        lang = self.language()
        done = 0
        try:
            for key, item in self._tmdb_todo(data):
                match = await self._async_match(session, api_key, key, item, data)
                found: dict[str, Any] = {"v": LOOKUP_VERSION}
                if match and match.kind == "tv" and match.season is None:
                    match.season = await self._async_season_at_release(session, api_key, match, item, lang)
                if match:
                    found |= {
                        "kind": match.kind,
                        "id": match.id,
                        "season": match.season,
                        "overview": match.overview,
                        "release_date": match.release_date,
                    }
                    if match.kind == "collection":
                        found["parts"] = await self._async_box_set_films(session, api_key, match, item, lang)
                    try:
                        # Countries for the statistics, genres for the titles the export leaves without.
                        found |= await tmdb.async_details(session, api_key, match, found.get("parts") or [], lang)
                    except tmdb.TmdbAuthError:
                        raise
                    except tmdb.TmdbError:
                        found |= {"countries": [], "genres": [], "rating": None}
                    posters = await tmdb.async_posters(session, api_key, match, lang)
                    if best := tmdb.best_poster(posters, lang):
                        found.update(
                            path=best["path"], width=best["width"], height=best["height"], lang=best["lang"]
                        )
                self.store.covers[key] = found
                done += 1
                if done % 25 == 0:
                    await self.store.async_save()
                    self.async_update_listeners()
        except tmdb.TmdbError as err:
            _LOGGER.warning("TMDB lookups stopped: %s", err)
        else:
            done += await self._async_fetch_omdb(session, data)
        finally:
            self._fetching = False
            if done:
                await self.store.async_save()
                if self.offline:
                    # Box sets without discs get their films from the TMDB collections.
                    self.async_set_updated_data(self._offline_data())
                else:
                    self.async_update_listeners()

    def entry_for(self, title: CollectionTitle) -> CatalogEntry | None:
        """Catalog data of a title, when the export knows it."""
        return self.store.catalog.get(title.collection_number)

    def find_child(self, key: str) -> BoxSetChild | None:
        """A box-set film by its lower-case ID."""
        if self.data:
            for children in self.data.box_sets.values():
                for child in children:
                    if child.id.lower() == key:
                        return child
        return None

    def _tmdb_cover(self, key: str) -> dict[str, Any] | None:
        found = self.store.covers.get(key) or {}
        if not found.get("path"):
            return None
        return {
            "source": "tmdb",
            "url": f"{TMDB_IMAGE_URL}{found['path']}",
            "width": found.get("width", 0),
            "height": found.get("height", 0),
        }

    def mymovies_cover(self, key: str) -> dict[str, Any] | None:
        """The My Movies cover of a title (API thumbnail) or box-set film (catalog cover)."""
        if self.offline:
            return None  # the thumbnails came from the API
        if self.data and key in self.data.titles:
            return {
                "source": "mymovies",
                "sign": THUMBNAIL_PATH.format(
                    entry_id=self.config_entry.entry_id, title_id=self.data.titles[key].id
                ),
                "width": MYMOVIES_THUMBNAIL[0],
                "height": MYMOVIES_THUMBNAIL[1],
            }
        child = self.find_child(key)
        if child and child.thumbnail:
            return {
                "source": "mymovies",
                "url": child.thumbnail,
                "width": child.thumbnail_width or 200,
                "height": child.thumbnail_height or 0,
            }
        return None

    def cover(self, key: str) -> dict[str, Any] | None:
        """Cover of a title or box-set film: the user's choice, else the largest one.

        Returns {"source", "width", "height"} with "url" (public image) or "sign"
        (Home Assistant path to sign for the viewer).
        """
        if override := self.store.overrides.get(key):
            if override["source"] == "tmdb":
                return {
                    "source": "tmdb",
                    "url": f"{TMDB_IMAGE_URL}{override['path']}",
                    "width": override.get("width", 0),
                    "height": override.get("height", 0),
                    "chosen": True,
                }
            if override["source"] == "upload":
                return {
                    "source": "upload",
                    "sign": COVER_PATH.format(entry_id=self.config_entry.entry_id, key=key),
                    "width": override.get("width", 0),
                    "height": override.get("height", 0),
                    "chosen": True,
                }
            if mymovies := self.mymovies_cover(key):
                return {**mymovies, "chosen": True}
        candidates = [c for c in (self._tmdb_cover(key), self.mymovies_cover(key)) if c]
        if self.data and key in self.data.box_sets and not any(c["source"] == "tmdb" for c in candidates):
            # Box set unknown to TMDB: the poster of one of its films.
            for child in self.data.box_sets[key]:
                child_key = self.data.child_titles.get(child.id.lower(), child.id.lower())
                if poster := self._tmdb_cover(child_key):
                    candidates.append(poster)
                    break
        return max(candidates, key=lambda c: c["width"] * c["height"], default=None)

    @staticmethod
    def _apply_cover(data: dict[str, Any], cover: dict[str, Any] | None) -> None:
        """Poster URL (when public), cover description and the path to sign, if any."""
        data["poster"] = cover.get("url") if cover else None
        data["cover"] = (
            {k: cover[k] for k in ("source", "width", "height")} | {"chosen": cover.get("chosen", False)}
            if cover
            else None
        )
        data["_sign"] = cover.get("sign") if cover else None

    def describe_child(self, child: BoxSetChild) -> dict[str, Any]:
        """One film of a box set, for the panel."""
        key = child.id.lower()
        data = {
            "id": child.id,
            "title": child.title,
            "original_title": child.original_title,
            "year": child.year,
            "edition": child.edition,
            "disc_type": child.disc_type,
            "description": (self.store.covers.get(key) or {}).get("overview", ""),
            "film_release_date": (self.store.covers.get(key) or {}).get("release_date", ""),
            "watched": self._child_watched(child),
            "title_id": self.data.child_titles.get(key) if self.data else None,
        }
        data["viewings"] = (self.store.viewings.get(data["title_id"] or key) or {}).get("dates", [])
        self._apply_details(data, key)
        # A disc owned as its own title has the export's genres, else TMDB's.
        title = self.data.titles.get(data["title_id"]) if self.data and data["title_id"] else None
        entry = self.entry_for(title) if title else None
        data["genres"] = (
            (entry.genres if entry else [])
            or (self.store.covers.get(key) or {}).get("genres")
            or self._omdb(key).get("genres", [])
        )
        data["rating"] = (
            (entry.rating if entry else None)
            or (self.store.covers.get(key) or {}).get("rating")
            or self._omdb(key).get("rating")
        )
        self._apply_cover(data, self.cover(key))
        return data

    def _apply_details(self, data: dict[str, Any], key: str) -> None:
        """Genres and countries chosen by the user win over the export's and TMDB's."""
        chosen = self.store.details.get(key) or {}
        for name in ("genres", "countries"):
            data[f"{name}_manual"] = bool(chosen.get(name))
            if chosen.get(name):
                data[name] = chosen[name]

    def _child_watched(self, child: BoxSetChild) -> bool:
        """A box-set film owned as its own title is watched when that title is."""
        if not self.data:
            return False
        if title_id := self.data.child_titles.get(child.id.lower()):
            return self.data.titles[title_id].watched
        if self.offline:
            return self.local_watched(child.id, False)
        return self.data.children_watched.get(child.id.lower(), False)

    def describe(self, title: CollectionTitle, *, details: bool = False) -> dict[str, Any]:
        """Everything known about a title (details: also the export columns and box set)."""
        entry = self.entry_for(title)
        key = title.id.lower()
        data: dict[str, Any] = {
            "id": title.id,
            "collection_number": title.collection_number,
            "title": entry.title if entry else None,
            "original_title": entry.original_title if entry else None,
            "imdb": entry.imdb if entry else None,
            "year": entry.year if entry else None,
            "watched": title.watched,
            "viewings": (self.store.viewings.get(key) or {}).get("dates", []),
        }
        self._apply_cover(data, self.cover(key))
        children = self.data.box_sets.get(key, []) if self.data else []
        if details:
            default = CatalogEntry("", "", "", None, None)
            for name in DETAIL_FIELDS:
                data[name] = getattr(entry or default, name)
            if not data["description"]:
                data["description"] = (self.store.covers.get(key) or {}).get("overview", "")
            data["film_release_date"] = (self.store.covers.get(key) or {}).get("release_date", "")
            omdb_data = self._omdb(key)  # IMDb data, only for what TMDB left empty
            data["countries"] = (self.store.covers.get(key) or {}).get("countries") or omdb_data.get("countries", [])
            data["runtime"] = data["runtime"] or omdb_data.get("runtime")
            data["director"] = data["director"] or omdb_data.get("director", "")
            # Box sets have no genre in the export: TMDB gives those of their films.
            data["genres"] = (
                data["genres"] or (self.store.covers.get(key) or {}).get("genres") or omdb_data.get("genres", [])
            )
            data["children"] = [self.describe_child(c) for c in children]
            # A box set TMDB does not know takes the genres of its films.
            data["genres"] = data["genres"] or list(
                dict.fromkeys(g for c in data["children"] for g in c["genres"])
            )
            # Missing ratings: TMDB's for a film, the average of its films for a box set.
            if data["rating"] is None:
                rated = [c["rating"] for c in data["children"] if c["rating"] is not None]
                data["rating"] = (
                    round(sum(rated) / len(rated), 1)
                    if rated
                    else (self.store.covers.get(key) or {}).get("rating") or omdb_data.get("rating")
                )
            data["box_set_id"] = self.data.box_of.get(key) if self.data else None
            self._apply_details(data, key)
        else:
            data.pop("_sign")
            data.pop("cover")
            if children:
                keep = ("id", "title", "original_title", "year", "watched", "title_id")
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
