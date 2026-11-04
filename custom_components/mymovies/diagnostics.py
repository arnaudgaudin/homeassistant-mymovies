"""Diagnostics for the My Movies integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import MyMoviesConfigEntry

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, "title", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyMoviesConfigEntry
) -> dict[str, Any]:
    """Return the entry (credentials redacted) and a summary of the collection."""
    titles = list(entry.runtime_data.data.titles.values())
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "titles": len(titles),
        "watched": sum(t.watched for t in titles),
        "sample": [asdict(t) for t in titles[:3]],
    }
