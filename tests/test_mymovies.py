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
def no_tmdb_network():
    """TMDB is never reached for real: tests patch the lookups they need."""
    from custom_components.mymovies import tmdb

    with patch.object(tmdb, "_get", AsyncMock(side_effect=tmdb.TmdbError("no network in tests"))):
        yield


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
        "Running Time,Rating,Genres,Actors,Description,3D\n"
        '1,"Le Seigneur des anneaux","The Lord of the Rings","Seigneur",tt0120737,2001,'
        '2:58,8.9," Fantasy, Adventure"," Elijah Wood, Ian McKellen","Un anneau.; Une quête.; ; Een ring.",yes\n'
        '2,"Trilogie","Trilogie","Trilogie",tt0000000,,,,,,-,no\n',
        encoding="utf-8",
    )
    catalog = parse_export(path)
    assert catalog[1].original_title == "The Lord of the Rings"
    assert catalog[1].imdb == "tt0120737" and catalog[1].year == 2001
    assert catalog[1].runtime == 178 and catalog[1].rating == 8.9
    assert catalog[1].three_d and not catalog[2].three_d
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


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="me@example.com",
        title="me@example.com",
        data={CONF_USERNAME: "me@example.com", CONF_PASSWORD: "secret"},
        options=options or {},
    )
    entry.add_to_hass(hass)
    with (
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
        patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS),
        patch(f"{CLIENT}.async_get_titles_in_box_set", return_value=[]),
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
    store.covers = {
        TITLES[0].id.lower(): {"kind": "movie", "id": 1, "path": "/sincity.jpg", "width": 2000, "height": 3000},
        "child-2": {"kind": "movie", "id": 2, "path": "/reloaded.jpg", "width": 1000, "height": 1500, "overview": "Neo revient."},
    }

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "mymovies/collection"})
    msg = await client.receive_json()
    assert msg["success"]
    titles = {t["collection_number"]: t for t in msg["result"]["titles"]}
    assert titles[1]["poster"] == "https://image.tmdb.org/t/p/w342/sincity.jpg"
    assert titles[1]["cover"] == {"source": "tmdb", "width": 2000, "height": 3000, "chosen": False}
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


async def test_import_from_panel(hass: HomeAssistant, hass_ws_client, hass_admin_user) -> None:
    """Admins import an export from the panel; bad files and non-admins are refused."""
    entry = await _setup(hass)
    reader = "custom_components.mymovies.websocket.read_uploaded_export"
    client = await hass_ws_client(hass)
    with (
        patch(reader, return_value=CATALOG),
        patch(f"{CLIENT}.async_get_titles", return_value=TITLES),
        patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS),
    ):
        await client.send_json_auto_id({"type": "mymovies/import_export", "file_id": "abc"})
        msg = await client.receive_json()
    assert msg["success"] and msg["result"] == {"count": 4}
    assert entry.runtime_data.store.catalog == CATALOG
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"catalog_{entry.entry_id}") is None

    with patch(reader, side_effect=InvalidExportError("missing columns")):
        await client.send_json_auto_id({"type": "mymovies/import_export", "file_id": "abc"})
        msg = await client.receive_json()
    assert not msg["success"] and msg["error"]["code"] == "invalid_export"

    hass_admin_user.groups = []  # no longer an administrator
    await client.send_json_auto_id({"type": "mymovies/import_export", "file_id": "abc"})
    msg = await client.receive_json()
    assert not msg["success"] and msg["error"]["code"] == "unauthorized"


async def test_box_set_discs_owned_as_titles(hass: HomeAssistant, hass_ws_client) -> None:
    """A box-set disc also scanned as its own title is shown and resolved through that title."""
    titles = [*TITLES, _title(5, watched=True)]
    catalog = {**CATALOG, 5: CatalogEntry("Matrix Reloaded", "The Matrix Reloaded", "Matrix 2", "tt0234215", 2003)}
    entry = await _setup(hass)
    coordinator = entry.runtime_data
    coordinator.store.catalog = catalog
    with (
        patch(f"{CLIENT}.async_get_titles", return_value=titles),
        patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS),
    ):
        await coordinator.async_refresh()
    disc = titles[4].id.lower()
    box = titles[3].id.lower()
    assert coordinator.data.child_titles == {"child-2": disc}
    assert coordinator.data.box_of == {disc: box}

    with patch.object(coordinator.client, "async_mark_watched", AsyncMock()) as mark, patch(
        f"{CLIENT}.async_get_titles", return_value=titles
    ), patch(f"{CLIENT}.async_get_box_set_children", return_value=BOX_SETS):
        await hass.services.async_call(DOMAIN, "mark_watched", {"title": "matrix reloaded"}, blocking=True)
    assert mark.await_args.args[0] == titles[4].id  # the title, not the catalog film

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "mymovies/collection"})
    result = {t["collection_number"]: t for t in (await client.receive_json())["result"]["titles"]}
    assert result[5]["box_set_id"] == box
    reloaded = next(c for c in result[4]["children"] if c["id"] == "child-2")
    assert reloaded["title_id"] == disc and reloaded["watched"] is True



def test_tmdb_rules() -> None:
    """Poster ranking, season numbers and box-set collection names."""
    from custom_components.mymovies import tmdb

    posters = [
        {"path": "/en.jpg", "width": 2000, "height": 3000, "lang": "en", "votes": 9},
        {"path": "/fr_small.jpg", "width": 600, "height": 900, "lang": "fr", "votes": 9},
        {"path": "/fr.jpg", "width": 1800, "height": 2700, "lang": "fr", "votes": 3},
    ]
    assert tmdb.best_poster(posters, "fr")["path"] == "/fr.jpg"  # sharp and French
    assert tmdb.season_number("Dark Angel: The Complete Second Season") == 2
    assert tmdb.season_number("Stargate SG-1 : Saison 3") == 3
    assert tmdb.season_number("Apollo 11") is None
    wanted = tmdb._bare(tmdb.franchise_name("Jurassic World : Trilogie"))
    assert tmdb._bare("Collection Jurassic World").startswith(wanted)
    assert not tmdb._bare("LEGO Jurassic World Collection").startswith(wanted)


def test_image_size() -> None:
    """Uploaded covers: PNG and JPEG sizes are read, anything else is refused."""
    import struct

    from custom_components.mymovies.covers import InvalidImageError, image_size

    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 1000, 1500)
    assert image_size(png) == ("png", 1000, 1500)
    jpeg = b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"JF" + b"\xff\xc0" + struct.pack(">HBHH", 17, 8, 1500, 1000)
    assert image_size(jpeg) == ("jpg", 1000, 1500)
    with pytest.raises(InvalidImageError):
        image_size(b"GIF89a....")


async def test_tmdb_lookup(hass: HomeAssistant) -> None:
    """Each season disc gets its season's poster; titles without IMDb ID are searched."""
    from custom_components.mymovies import tmdb

    titles = [_title(1), _title(2), _title(3)]
    catalog = {
        1: CatalogEntry("Dark Angel: The Complete First Season", "Dark Angel: The Complete First Season", "DA1", "tt0204993", 2000),
        2: CatalogEntry("Dark Angel: The Complete Second Season", "Dark Angel: The Complete Second Season", "DA2", "tt0204993", 2001),
        3: CatalogEntry("Renaissance", "Renaissance", "Renaissance", None, 2006),
    }
    entry = await _setup(hass, {"tmdb_api_key": "k"})
    coordinator = entry.runtime_data
    coordinator.store.catalog = catalog
    seasons = []

    async def posters(session, key, match, lang):
        seasons.append((match.kind, match.season))
        return [{"path": f"/{match.kind}{match.season or ''}.jpg", "width": 2000, "height": 3000, "lang": "fr", "votes": 5}]

    with (
        patch.object(tmdb, "async_find_imdb", AsyncMock(side_effect=lambda *a: tmdb.TmdbMatch("tv", 2407))),
        patch.object(tmdb, "async_search_movie", AsyncMock(return_value=tmdb.TmdbMatch("movie", 9389))) as search,
        patch.object(tmdb, "async_posters", side_effect=posters),
        patch(f"{CLIENT}.async_get_titles", return_value=titles),
        patch(f"{CLIENT}.async_get_box_set_children", return_value={}),
        patch(f"{CLIENT}.async_get_titles_in_box_set", return_value=[]),
    ):
        await coordinator.async_refresh()  # schedules the TMDB lookups
        await hass.async_block_till_done()
    covers = coordinator.store.covers
    assert covers[titles[0].id.lower()]["path"] == "/tv1.jpg"
    assert covers[titles[1].id.lower()]["path"] == "/tv2.jpg"
    assert covers[titles[2].id.lower()]["path"] == "/movie.jpg"
    assert search.await_args.args[2] == "Renaissance"


async def test_cover_choice(hass: HomeAssistant, hass_ws_client) -> None:
    """Largest cover by default; the user can pick a TMDB poster, upload one, or go back."""
    import struct

    from custom_components.mymovies import tmdb

    entry = await _setup(hass, {"tmdb_api_key": "k"})
    coordinator = entry.runtime_data
    key = TITLES[0].id.lower()
    # Small TMDB poster: still larger than the My Movies thumbnail.
    coordinator.store.covers = {key: {"kind": "movie", "id": 1, "path": "/small.jpg", "width": 300, "height": 450}}
    assert coordinator.cover(key)["source"] == "tmdb"
    coordinator.store.covers = {key: {"kind": "movie", "id": 1}}
    assert coordinator.cover(key)["source"] == "mymovies"

    client = await hass_ws_client(hass)
    choices = [{"path": "/a.jpg", "width": 2000, "height": 3000, "lang": "fr", "votes": 1}]
    with patch.object(tmdb, "async_posters", AsyncMock(return_value=choices)):
        await client.send_json_auto_id({"type": "mymovies/cover_choices", "title_id": TITLES[0].id})
        msg = await client.receive_json()
    assert msg["success"]
    assert [c["source"] for c in msg["result"]["choices"]] == ["tmdb", "mymovies"]

    await client.send_json_auto_id(
        {"type": "mymovies/set_cover", "title_id": TITLES[0].id, "source": "tmdb", "path": "/a.jpg", "width": 2000, "height": 3000}
    )
    assert (await client.receive_json())["success"]
    assert entry.runtime_data.cover(key) | {} == {
        "source": "tmdb", "url": "https://image.tmdb.org/t/p/w342/a.jpg", "width": 2000, "height": 3000, "chosen": True,
    }

    png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 800, 1200)
    with patch("custom_components.mymovies.websocket.read_upload", return_value=png):
        await client.send_json_auto_id({"type": "mymovies/set_cover", "title_id": TITLES[0].id, "source": "upload", "file_id": "f"})
        assert (await client.receive_json())["success"]
    cover = entry.runtime_data.cover(key)
    assert cover["source"] == "upload" and cover["width"] == 800
    path = Path(hass.config.path("mymovies", "covers", f"{entry.entry_id}_{key}.png"))
    assert path.is_file()

    await client.send_json_auto_id({"type": "mymovies/set_cover", "title_id": TITLES[0].id, "source": "auto"})
    assert (await client.receive_json())["success"]
    assert not path.exists()  # the uploaded file is removed with the choice
    assert entry.runtime_data.cover(key)["source"] == "mymovies"


async def test_offline_from_export(hass: HomeAssistant) -> None:
    """When My Movies refuses its API, the collection comes from the imported export."""
    from homeassistant.exceptions import HomeAssistantError

    entry = await _setup(hass)
    coordinator = entry.runtime_data
    coordinator.store.catalog = {
        **CATALOG,
        5: CatalogEntry("Up", "Up", "Up", "tt1049413", 2009, watched=True),
    }
    refused = MyMoviesAuthError("GetTitlesInCollection: credentials rejected")
    with patch(f"{CLIENT}.async_get_titles", side_effect=refused):
        await coordinator.async_refresh()
    assert coordinator.last_update_success and coordinator.offline
    titles = {t.collection_number: t for t in coordinator.data.titles.values()}
    assert sorted(titles) == [1, 2, 3, 4, 5] and titles[5].watched
    assert coordinator.data.box_sets == {}
    assert coordinator.mymovies_cover(titles[1].id.lower()) is None
    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(DOMAIN, "mark_watched", {"title": "Up"}, blocking=True)
    assert err.value.translation_key == "offline"

    # Without any export, refusals still ask to sign in again.
    coordinator.store.catalog = {}
    with patch(f"{CLIENT}.async_get_titles", side_effect=refused):
        await coordinator.async_refresh()
    assert not coordinator.last_update_success


def test_box_sets_from_sort_titles() -> None:
    """Discs are found under their box set's sort title, whatever its case or article."""
    from custom_components.mymovies.catalog import link_box_sets

    def entry(title, sort, imdb=None):
        return CatalogEntry(title, title, sort, imdb, None)

    catalog = {
        23: entry("The Matrix Trilogy", "Matrix Trilogy, The"),
        25: entry("The Matrix", "Matrix Trilogy, The 01: The Matrix", "tt0133093"),
        24: entry("The Matrix Revolutions", "Matrix Trilogy, The 03: The Matrix Revolutions", "tt0242653"),
        43: entry("Retour vers le futur : Trilogie", "Retour vers le futur : Trilogie"),
        45: entry("Retour vers le futur", "Retour vers Le Futur: Trilogie 01: Retour vers le futur 01", "tt0088763"),
        138: entry("Sans un Bruit", "Quiet Place Collection, A"),
        139: entry("Sans un Bruit", "Quiet Place Collection 01: Sans un Bruit, A", "tt6644200"),
        42: entry("Sin City 2", "Sin City 02: J'ai tue pour elle", "tt0458481"),  # saga order, no box set
    }
    link_box_sets(catalog)
    assert (catalog[25].box, catalog[25].box_order) == (23, 1)
    assert (catalog[24].box, catalog[24].box_order) == (23, 3)
    assert catalog[45].box == 43 and catalog[139].box == 138
    assert catalog[42].box is None and catalog[23].box is None


async def test_offline_box_sets(hass: HomeAssistant) -> None:
    """Offline, box sets come from the export, or from TMDB collections up to their release."""
    from custom_components.mymovies.catalog import link_box_sets

    entry = await _setup(hass)
    coordinator = entry.runtime_data
    catalog = {
        23: CatalogEntry("The Matrix Trilogy", "The Matrix Trilogy", "Matrix Trilogy, The", None, None),
        25: CatalogEntry("The Matrix", "The Matrix", "Matrix Trilogy, The 01: The Matrix", "tt0133093", 1999),
        26: CatalogEntry("The Matrix Reloaded", "The Matrix Reloaded", "Matrix Trilogy, The 02: Reloaded", "tt0234215", 2003, watched=True),
        183: CatalogEntry("Jurassic World : Trilogie", "Jurassic World: Trilogy", "Jurassic World : Trilogie", None, None, release_date="2025-06-24"),
    }
    link_box_sets(catalog)
    coordinator.store.catalog = catalog
    box_key = "00000000-0000-0000-0000-000000000183"
    coordinator.store.covers[box_key] = {
        "kind": "collection",
        "id": 328,
        "parts": [
            {"id": 135397, "title": "Jurassic World", "original_title": "Jurassic World", "release_date": "2015-06-10", "year": 2015, "poster": "/jw.jpg", "overview": ""},
            {"id": 351286, "title": "Fallen Kingdom", "original_title": "Fallen Kingdom", "release_date": "2018-06-06", "year": 2018, "poster": "/fk.jpg", "overview": ""},
            {"id": 1234821, "title": "Rebirth", "original_title": "Rebirth", "release_date": "2025-07-02", "year": 2025, "poster": "/rb.jpg", "overview": ""},
        ],
    }
    with patch(f"{CLIENT}.async_get_titles", side_effect=MyMoviesAuthError("refused")):
        await coordinator.async_refresh()
    data = coordinator.data
    matrix = data.box_sets["00000000-0000-0000-0000-000000000023"]
    assert [c.title for c in matrix] == ["The Matrix", "The Matrix Reloaded"]
    reloaded = "00000000-0000-0000-0000-000000000026"
    assert data.box_of[reloaded] == "00000000-0000-0000-0000-000000000023"
    assert coordinator.describe_child(matrix[1])["watched"] is True
    assert [c.title for c in data.box_sets[box_key]] == ["Jurassic World", "Fallen Kingdom"]  # no Rebirth
    assert coordinator.describe_child(data.box_sets[box_key][0])["poster"] == "https://image.tmdb.org/t/p/w342/jw.jpg"


async def test_offline_when_every_call_is_refused(hass: HomeAssistant) -> None:
    """The box-set call being refused too must not hide the titles' refusal."""
    from custom_components.mymovies.api import MyMoviesError

    entry = await _setup(hass)
    coordinator = entry.runtime_data
    coordinator.store.catalog = CATALOG
    with (
        patch(f"{CLIENT}.async_get_titles", side_effect=MyMoviesAuthError("refused")),
        patch(f"{CLIENT}.async_get_box_set_children", side_effect=MyMoviesError("refused")),
    ):
        await coordinator.async_refresh()
    assert coordinator.last_update_success and coordinator.offline
