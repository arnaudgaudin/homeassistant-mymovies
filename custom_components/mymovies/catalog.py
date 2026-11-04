"""Titles and details that the credentials-only API does not provide.

The My Movies API only exposes catalog data (names, IMDb IDs, synopsis...) to
the official apps. The integration therefore imports the collection export of
the My Movies app (CSV) and joins it to the API by collection number. TMDB
lookups (posters by IMDb ID, box-set films by title) are cached next to it.
"""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

from homeassistant.components.file_upload import process_uploaded_file
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

REQUIRED_COLUMNS = {"Collection Number", "Title", "IMDB Id"}
NO_IMDB = "tt0000000"  # what the export holds for box sets
MAX_ACTORS = 15  # searchable; the dialog shows the first 8


class InvalidExportError(Exception):
    """The file is not a My Movies collection export."""


@dataclass(slots=True)
class CatalogEntry:
    """Descriptive data of one title, from the export."""

    title: str
    original_title: str
    sort_title: str
    imdb: str | None
    year: int | None
    runtime: int | None = None  # minutes
    rating: float | None = None
    personal_rating: float | None = None
    parental_rating: str = ""
    release_date: str = ""  # YYYY-MM-DD
    added: str = ""  # YYYY-MM-DD
    disc_type: str = ""
    three_d: bool = False
    media_type: str = ""
    group: str = ""
    edition: str = ""
    genres: list[str] = field(default_factory=list)
    director: str = ""
    actors: list[str] = field(default_factory=list)
    description: str = ""
    watched: bool = False
    box: int | None = None  # collection number of the box set this disc belongs to
    box_order: int | None = None  # position of the disc in its box set


def normalize_title(text: str | None) -> str:
    """Case- and accent-insensitive form of a title, for matching."""
    decomposed = unicodedata.normalize("NFKD", (text or "").casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip()


def _minutes(value: str) -> int | None:
    """'1:58' -> 118."""
    hours, _, minutes = value.partition(":")
    if hours.isdigit() and minutes.isdigit():
        return int(hours) * 60 + int(minutes)
    return None


def _number(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _names(value: str, limit: int | None = None) -> list[str]:
    names = [part.strip() for part in value.split(",") if part.strip()]
    return names[:limit] if limit else names


def parse_export(path: Path) -> dict[int, CatalogEntry]:
    """Read a My Movies collection export (CSV), keyed by collection number.

    Blocking: run it in the executor.
    """
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise InvalidExportError(f"missing columns: {sorted(missing)}")
        catalog: dict[int, CatalogEntry] = {}
        for row in reader:
            col = {k: (v or "").strip() for k, v in row.items() if k}
            number = col.get("Collection Number", "")
            if not number.isdigit():
                continue
            title = col.get("Title", "")
            imdb = col.get("IMDB Id", "")
            year = col.get("Production Year", "")
            # The description holds one text per language, separated by "; ;".
            description = col.get("Description", "").split("; ;")[0].strip(" ;")
            # Paragraphs are separated by ";" after the end of a sentence.
            description = re.sub(r"([.!?…»])\s*;\s*", "\\1\n", description)
            catalog[int(number)] = CatalogEntry(
                title=title,
                original_title=col.get("Original Title") or title,
                sort_title=col.get("Sort Title") or title,
                imdb=imdb if imdb.startswith("tt") and imdb != NO_IMDB else None,
                year=int(year) if year.isdigit() else None,
                runtime=_minutes(col.get("Running Time", "")),
                rating=_number(col.get("Rating", "")),
                personal_rating=_number(col.get("Personal Rating", "")),
                parental_rating=col.get("Par. Rating", ""),
                release_date=col.get("Release Date", ""),
                added=col.get("Added Date", ""),
                disc_type=col.get("Disc Type", ""),
                three_d=col.get("3D", "").lower() == "yes",
                media_type=col.get("Media Type", ""),
                group=col.get("Group", ""),
                edition=col.get("Edition", ""),
                genres=_names(col.get("Genres", "")),
                director=col.get("Director", ""),
                actors=_names(col.get("Actors", ""), MAX_ACTORS),
                description="" if description == "-" else description,
                watched=col.get("Watched", "").lower() == "yes",
            )
    if not catalog:
        raise InvalidExportError("no titles in the file")
    link_box_sets(catalog)
    return catalog


_SORT_DISC = re.compile(r"^(.*?) (\d+): ")
_TRAILING_ARTICLE = re.compile(r",\s*(the|a|an|le|la|les|l')$")


def _sort_key(text: str) -> str:
    """'Quiet Place Collection, A' and 'Retour vers Le Futur: Trilogie' compare as written."""
    key = _TRAILING_ARTICLE.sub("", normalize_title(text))
    key = re.sub(r"\s*:\s*", ": ", key)
    return re.sub(r"\s+", " ", key).strip()


def link_box_sets(catalog: dict[int, CatalogEntry]) -> None:
    """Find the discs of each box set from the export's sort titles.

    My Movies sorts the discs of a box set under the box set's sort title followed
    by their position: "Matrix Trilogy, The" holds "Matrix Trilogy, The 01: The
    Matrix", "Matrix Trilogy, The 02: ...". Box sets have no IMDb ID.
    """
    boxes = {_sort_key(e.sort_title): number for number, e in catalog.items() if e.imdb is None}
    for number, entry in catalog.items():
        entry.box = entry.box_order = None
        if match := _SORT_DISC.match(entry.sort_title):
            box = boxes.get(_sort_key(match.group(1)))
            if box is not None and box != number:
                entry.box, entry.box_order = box, int(match.group(2))


def read_uploaded_export(hass: HomeAssistant, file_id: str) -> dict[int, CatalogEntry]:
    """Parse an export uploaded through Home Assistant (runs in the executor)."""
    with process_uploaded_file(hass, file_id) as path:
        return parse_export(Path(path))


class CatalogStore:
    """Persist the imported catalog, the TMDB lookups and the covers chosen by the user.

    covers: lower-case title or film ID -> TMDB match and best poster
        ({"kind", "id", "overview", "path", "width", "height", "lang"}; {} when TMDB
        does not know it).
    overrides: lower-case title or film ID -> cover chosen by the user
        ({"source": "tmdb", "path", ...}, {"source": "mymovies"} or
        {"source": "upload", "file", ...}).
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self.catalog: dict[int, CatalogEntry] = {}
        self.covers: dict[str, dict] = {}
        self.overrides: dict[str, dict] = {}

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.catalog = {int(k): CatalogEntry(**v) for k, v in data.get("catalog", {}).items()}
        self.covers = data.get("covers", {})
        self.overrides = data.get("overrides", {})

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "catalog": {str(k): asdict(v) for k, v in self.catalog.items()},
                "covers": self.covers,
                "overrides": self.overrides,
            }
        )

    async def async_remove(self) -> None:
        await self._store.async_remove()
