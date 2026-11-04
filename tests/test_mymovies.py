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

from custom_components.mymovies.api import BoxSetChild, CollectionTitle, MyMoviesAuthError
from custom_components.mymovies.catalog import CatalogEntry, InvalidExportError, parse_export
from custom_components.mymovies.const import DOMAIN

CLIENT = "custom_components.mymovies.api.MyMoviesClient"


@pytest.fixture(autouse=True)
def films_not_watched():
    """Box-set films start unwatched (their flag is read one by one)."""
    with patch(f"{CLIENT}.async_get_watched", return_value=False) as mock:
        yield mock


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


TITLES = [_title(1), _title(2, watched=True), _title(3), _title(4)]
BOX_SETS = {
    TITLES[3].id.lower(): [
        BoxSetChild("child-1", TITLES[3].id.lower(), "Matrix", "The Matrix", 1999, "", "4K Ultra HD", "https://cdn/1.jpg"),
        BoxSetChild("child-2", TITLES[3].id.lower(), "Matrix Reloaded", "The Matrix Reloaded", 2003, "", "4K Ultra HD", ""),
    ]
}
CATALOG = {
    1: CatalogEntry("Sin City", "Sin City", "Sin City", "tt0401792", 2005),
    2: CatalogEntry("Avatar", "Avatar", "Avatar", "tt0499549", 2009),
    3: CatalogEntry("Avatar", "Avatar", "Avatar", "tt0499549", 2009),
    4: CatalogEntry("The Matrix Trilogy", "The Matrix Trilogy", "Matrix", None, 1999),
}


def test_parse_export(tmp_path: Path) -> None:
    """The export is keyed by collection number; box sets get no IMDb ID."""
    path = tmp_path / "export.csv"
    path.write_text(
        "\ufeffCollection Number,Title,Original Title,Sort Title,IMDB Id,Production Year,"
        "Running Time,Rating,Genres,Actors,Description\n"
        '1,"Le Seigneur des anneaux","The Lord of the Rings","Seigneur",tt0120737,2001,'
        '2:58,8.9," Fantasy, Adventure"," Elijah Wood, Ian McKellen","Un anneau.; Une quête.; ; Een ring."\n'
        '2,"Trilogie","Trilogie","Trilogie",tt0000000,,,,,,-\n',
        encoding="utf-8",
    )
    catalog = parse_export(path)
    assert catalog[1].original_title == "The Lord of the Rings"
    assert catalog[1].imdb == "tt0120737" and catalog[1].year == 2001
    assert catalog[1].runtime == 178 and catalog[1].rating == 8.9
    assert catalog[1].genres == ["Fantasy", "Adventure"]
    assert catalog[1].actors == ["Elijah Wood", "Ian McKellen"]
    assert catalog[1].description == "Un anneau.\nUne quête."
    assert catalog[2].imdb is None and catalog[2].year is None
    assert catalog[2].description == "" and catalog[2].runtime is None

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
    with (
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
        patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_sensors_and_catalog_issue(hass: HomeAssistant) -> None:
    """Counts are exposed; a missing export raises a repair issue."""
    entry = await _setup(hass)
    assert hass.states.get("sensor.my_movies_me_example_com_titles").state == "4"
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
        patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS),
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



async def test_panel_and_websocket(hass: HomeAssistant, hass_ws_client) -> None:
    """The panel is registered and gets titles with details, box sets and covers."""
    entry = await _setup(hass)
    assert "mymovies" in hass.data["frontend_panels"]
    store = entry.runtime_data.store
    store.catalog = CATALOG
    store.posters = {"tt0401792": "/sincity.jpg"}
    store.children = {"child-2": {"poster": "/reloaded.jpg", "overview": "Neo revient."}}

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "mymovies/collection"})
    msg = await client.receive_json()
    assert msg["success"]
    titles = {t["collection_number"]: t for t in msg["result"]["titles"]}
    assert titles[1]["poster"] == "https://image.tmdb.org/t/p/w342/sincity.jpg"
    # No TMDB poster: signed My Movies thumbnail.
    assert titles[2]["poster"].startswith("/api/mymovies/thumbnail/") and "authSig=" in titles[2]["poster"]
    # Box set without collection poster: its first film with a TMDB poster.
    box = titles[4]
    assert box["poster"] == "https://image.tmdb.org/t/p/w342/reloaded.jpg"
    assert [c["title"] for c in box["children"]] == ["Matrix", "Matrix Reloaded"]
    assert box["children"][0]["poster"] == "https://cdn/1.jpg"
    assert box["children"][1]["description"] == "Neo revient."

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert "mymovies" not in hass.data["frontend_panels"]


async def test_box_sets_from_catalog(hass: HomeAssistant) -> None:
    """Box sets the user did not detail are read once from the catalog, then cached."""
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    coordinator.store.catalog = CATALOG
    films = [BoxSetChild("m1", "x", "The Matrix", "The Matrix", 1999, "", "4K Ultra HD", "")]
    with (
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
        patch(f"{CLIENT}.async_get_box_set_children", return_value={}),
        patch(f"{CLIENT}.async_get_titles_in_box_set", return_value=films) as per_box,
    ):
        await coordinator.async_refresh()
        await coordinator.async_refresh()
    # Only #4 has no IMDb ID: one call in total thanks to the cache.
    assert per_box.await_count == 1
    assert coordinator.data.box_sets[TITLES[3].id.lower()] == films


async def test_box_set_film_watched(hass: HomeAssistant) -> None:
    """A film inside a box set is marked by name; same name on its own disc is ambiguous."""
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    coordinator.store.catalog = CATALOG
    client = coordinator.client
    with (
        patch.object(client, "async_mark_watched", AsyncMock()) as mark,
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
        patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS),
    ):
        await hass.services.async_call(
            DOMAIN, "mark_watched", {"title": "Matrix Reloaded"}, blocking=True
        )
        assert mark.await_args.args[0] == "child-2"
    assert coordinator.data.children_watched["child-2"] is True

    response = await hass.services.async_call(
        DOMAIN, "get_titles", {}, blocking=True, return_response=True
    )
    box = next(t for t in response["titles"] if t["collection_number"] == 4)
    assert [(c["title"], c["watched"]) for c in box["children"]] == [
        ("Matrix", False),
        ("Matrix Reloaded", True),
    ]

    coordinator.store.catalog = {**CATALOG, 1: CatalogEntry("Matrix", "The Matrix", "Matrix", "tt0133093", 1999)}
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "mark_watched", {"title": "the matrix"}, blocking=True)
    assert err.value.translation_placeholders["numbers"] == "#1, #4 › Matrix"
