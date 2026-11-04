"""Diagnostics for the My Movies integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_TMDB_API_KEY
from .coordinator import MyMoviesConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, CONF_TMDB_API_KEY, "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyMoviesConfigEntry
) -> dict[str, Any]:
    """Return the entry (secrets redacted) and a summary of the collection."""
    coordinator = entry.runtime_data
    titles = list(coordinator.data.titles.values())
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "titles": len(titles),
        "watched": sum(t.watched for t in titles),
        "catalog_entries": len(coordinator.store.catalog),
        "titles_without_catalog": sum(coordinator.entry_for(t) is None for t in titles),
        "posters_cached": sum(bool(p) for p in coordinator.store.posters.values()),
        "box_sets": len(coordinator.data.box_sets),
        "box_set_films": sum(len(c) for c in coordinator.data.box_sets.values()),
        "box_set_posters": sum(bool(p) for p in coordinator.store.box_posters.values()),
        "sample": [asdict(t) for t in titles[:3]],
    }
