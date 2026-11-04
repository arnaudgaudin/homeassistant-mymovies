"""Tests for the My Movies integration (API calls are mocked)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir

from custom_components.mymovies.api import CollectionTitle, MyMoviesAuthError
from custom_components.mymovies.catalog import CatalogEntry, InvalidExportError, parse_export
from custom_components.mymovies.const import DOMAIN

CLIENT = "custom_components.mymovies.api.MyMoviesClient"


def _title(number: int, watched: bool = False) -> CollectionTitle:
    return CollectionTitle(
        id=f"0000000{number}-aaaa-bbbb-cccc-dddddddddddd",
        collection_number=number,
        watched=watched,
        group="Owned",
        added="",
        data_changed="",
        covers_changed="",
    )


TITLES = [_title(1), _title(2, watched=True), _title(3)]
CATALOG = {
    1: CatalogEntry("Sin City", "Sin City", "Sin City", "tt0401792", 2005),
    2: CatalogEntry("Avatar", "Avatar", "Avatar", "tt0499549", 2009),
    3: CatalogEntry("Avatar", "Avatar", "Avatar", "tt0499549", 2009),
}


def test_parse_export(tmp_path: Path) -> None:
    """The export is keyed by collection number; box sets get no IMDb ID."""
    path = tmp_path / "export.csv"
    path.write_text(
        "﻿Collection Number,Title,Original Title,Sort Title,IMDB Id,Production Year\n"
        '1,"Le Seigneur des anneaux","The Lord of the Rings","Seigneur",tt0120737,2001\n'
        '2,"Trilogie","Trilogie","Trilogie",tt0000000,\n',
        encoding="utf-8",
    )
    catalog = parse_export(path)
    assert catalog[1].original_title == "The Lord of the Rings"
    assert catalog[1].imdb == "tt0120737" and catalog[1].year == 2001
    assert catalog[2].imdb is None and catalog[2].year is None

    bad = tmp_path / "bad.csv"
    bad.write_text("Name,Year\nfoo,2000\n", encoding="utf-8")
    with pytest.raises(InvalidExportError):
        parse_export(bad)


async def test_config_flow(hass: HomeAssistant) -> None:
    """Bad credentials show an error; good ones create the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    data = {CONF_USERNAME: " me@example.com ", CONF_PASSWORD: "secret"}
    with patch(f"{CLIENT}.async_get_titles", side_effect=MyMoviesAuthError("no")):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["errors"] == {"base": "invalid_auth"}

    with (
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
        patch("custom_components.mymovies.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USERNAME] == "me@example.com"


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="me@example.com",
        title="me@example.com",
        data={CONF_USERNAME: "me@example.com", CONF_PASSWORD: "secret"},
    )
    entry.add_to_hass(hass)
    with patch(f"{CLIENT}.async_get_titles", return_value=TITLES):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_sensors_and_catalog_issue(hass: HomeAssistant) -> None:
    """Counts are exposed; a missing export raises a repair issue."""
    entry = await _setup(hass)
    assert hass.states.get("sensor.my_movies_me_example_com_titles").state == "3"
    assert hass.states.get("sensor.my_movies_me_example_com_watched_titles").state == "1"
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"catalog_{entry.entry_id}")
    assert issue is not None and issue.translation_key == "catalog_missing"


async def test_services(hass: HomeAssistant) -> None:
    """Titles resolve by name (accent-insensitive) or number; duplicates are refused."""
    entry = await _setup(hass)
    entry.runtime_data.store.catalog = CATALOG
    client = entry.runtime_data.client

    with (
        patch.object(client, "async_mark_watched", AsyncMock()) as mark,
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
    ):
        await hass.services.async_call(
            DOMAIN, "mark_watched", {"title": "sín city"}, blocking=True
        )
        assert mark.await_args.args[0] == TITLES[0].id

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "mark_watched", {"title": "Avatar"}, blocking=True
            )
        await hass.services.async_call(DOMAIN, "mark_watched", {"title": "3"}, blocking=True)
        assert mark.await_args.args[0] == TITLES[2].id

    response = await hass.services.async_call(
        DOMAIN, "get_titles", {}, blocking=True, return_response=True
    )
    first = response["titles"][0]
    assert first["title"] == "Sin City" and first["imdb"] == "tt0401792"


async def test_film_wall(hass: HomeAssistant) -> None:
    """The media source lists the titles sorted, with covers and watched marks."""
    from homeassistant.components import media_source
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "media_source", {})
    entry = await _setup(hass)
    entry.runtime_data.store.catalog = CATALOG
    entry.runtime_data.store.posters = {"tt0401792": "/sincity.jpg"}

    wall = await media_source.async_browse_media(hass, f"media-source://{DOMAIN}")
    names = [child.title for child in wall.children]
    assert names == ["Avatar (2009)", "✓ Avatar (2009)", "Sin City (2005)"] or names == [
        "✓ Avatar (2009)",
        "Avatar (2009)",
        "Sin City (2005)",
    ]
    sin_city = wall.children[-1]
    assert sin_city.thumbnail == "https://image.tmdb.org/t/p/w342/sincity.jpg"
    assert wall.children[0].thumbnail.startswith("/api/mymovies/thumbnail/")
