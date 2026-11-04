"""Titles and IMDb IDs that the credentials-only API does not provide.

The My Movies API only exposes catalog data (names, IMDb IDs) to the official
apps. The integration therefore imports the collection export of the My Movies
app (CSV) and joins it to the API by collection number. TMDB poster paths found
by IMDb ID are cached next to it.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

REQUIRED_COLUMNS = {"Collection Number", "Title", "IMDB Id"}
NO_IMDB = "tt0000000"  # what the export holds for box sets


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
            number = (row.get("Collection Number") or "").strip()
            if not number.isdigit():
                continue
            title = (row.get("Title") or "").strip()
            imdb = (row.get("IMDB Id") or "").strip()
            year = (row.get("Production Year") or "").strip()
            catalog[int(number)] = CatalogEntry(
                title=title,
                original_title=(row.get("Original Title") or "").strip() or title,
                sort_title=(row.get("Sort Title") or "").strip() or title,
                imdb=imdb if imdb.startswith("tt") and imdb != NO_IMDB else None,
                year=int(year) if year.isdigit() else None,
            )
    if not catalog:
        raise InvalidExportError("no titles in the file")
    return catalog


class CatalogStore:
    """Persist the imported catalog and the TMDB poster cache of one account."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self.catalog: dict[int, CatalogEntry] = {}
        self.posters: dict[str, str] = {}  # IMDb ID -> TMDB poster path ("" = none)

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.catalog = {int(k): CatalogEntry(**v) for k, v in data.get("catalog", {}).items()}
        self.posters = data.get("posters", {})

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "catalog": {str(k): asdict(v) for k, v in self.catalog.items()},
                "posters": self.posters,
            }
        )

    async def async_remove(self) -> None:
        await self._store.async_remove()
