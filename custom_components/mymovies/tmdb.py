"""Optional TMDB lookups (free TMDB API key): find each title, list its posters with sizes."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import aiohttp

from .catalog import normalize_title

TMDB_API = "https://api.themoviedb.org/3"
TIMEOUT = aiohttp.ClientTimeout(total=20)
GOOD_WIDTH = 1000  # posters at least this wide are all sharp enough


class TmdbError(Exception):
    """TMDB could not be reached or answered unexpectedly."""


class TmdbAuthError(TmdbError):
    """TMDB rejected the API key."""


@dataclass(slots=True)
class TmdbMatch:
    """A TMDB movie, series or collection."""

    kind: str  # "movie", "tv" or "collection"
    id: int
    overview: str = ""
    season: int | None = None  # a season of a series has its own posters
    release_date: str = ""  # the film's (or series') first release, YYYY-MM-DD


async def _get(session: aiohttp.ClientSession, path: str, params: dict[str, str]) -> dict:
    try:
        async with session.get(f"{TMDB_API}{path}", params=params, timeout=TIMEOUT) as resp:
            if resp.status == 401:
                raise TmdbAuthError("invalid API key")
            if resp.status != 200:
                raise TmdbError(f"HTTP {resp.status} on {path}")
            return await resp.json()
    except (aiohttp.ClientError, TimeoutError) as err:
        raise TmdbError(str(err)) from err


async def async_validate_key(session: aiohttp.ClientSession, api_key: str) -> None:
    """Raise TmdbAuthError when the key is not accepted."""
    await _get(session, "/configuration", {"api_key": api_key})


async def async_find_imdb(
    session: aiohttp.ClientSession, api_key: str, imdb: str, language: str
) -> TmdbMatch | None:
    """The movie or series with this IMDb ID."""
    data = await _get(
        session,
        f"/find/{imdb}",
        {"api_key": api_key, "external_source": "imdb_id", "language": language},
    )
    for kind, results in (("movie", "movie_results"), ("tv", "tv_results")):
        for result in data.get(results) or []:
            date = result.get("release_date") or result.get("first_air_date") or ""
            return TmdbMatch(kind, result["id"], result.get("overview") or "", release_date=date)
    return None


async def async_search_movie(
    session: aiohttp.ClientSession, api_key: str, title: str, year: int | None, language: str
) -> TmdbMatch | None:
    """Best movie match for a title (and year)."""
    params = {"api_key": api_key, "query": title, "language": language}
    if year:
        params["year"] = str(year)
    data = await _get(session, "/search/movie", params)
    for result in data.get("results") or []:
        return TmdbMatch(
            "movie", result["id"], result.get("overview") or "", release_date=result.get("release_date") or ""
        )
    return None


# Words of box-set titles that are not part of the franchise name.
_BOX_SET_NOISE = re.compile(
    r"(trilog(y|ie)|int[ée]grale|collection|coffret|saga|\d+\s*films?|"
    r"l[’']?[ée]dition.*|[ée]dition.*|anniversa\w*.*|box\s*set)",
    re.IGNORECASE,
)
_ARTICLE = re.compile(r"^(the|le|la|les|l')\s*", re.IGNORECASE)


def franchise_name(title: str) -> str:
    """'Harry Potter: L'Édition Anniversaire Collector' -> 'Harry Potter'."""
    name = _BOX_SET_NOISE.sub(" ", title)
    return re.sub(r"\s+", " ", name).strip(" :-–—")


_FILM_COUNT = re.compile(r"(\d+)\s*-?\s*films?\b")
_SERIES_WORDS = {"trilog": 3, "quadrilog": 4, "tetralog": 4}


def box_set_size(title: str) -> int | None:
    """Number of films a box-set title announces: "Trilogie" 3, "Intégrale 5 Films" 5."""
    text = normalize_title(title)
    for word, size in _SERIES_WORDS.items():
        if word in text:
            return size
    match = _FILM_COUNT.search(text)
    return int(match.group(1)) if match else None


def _bare(name: str | None) -> str:
    """Franchise name, normalized, without "Collection", "Saga"... nor a leading article.

    "Collection Jurassic World" and "The Matrix Collection" give "jurassic world" and "matrix".
    """
    return _ARTICLE.sub("", normalize_title(franchise_name(name or "")))


async def async_search_collection(
    session: aiohttp.ClientSession, api_key: str, title: str, language: str
) -> TmdbMatch | None:
    """The TMDB collection named after a box set's franchise.

    Only a collection whose name starts with the franchise matches: "Jurassic World"
    must not pick "LEGO Jurassic World".
    """
    query = franchise_name(title)
    if not query:
        return None
    data = await _get(
        session, "/search/collection", {"api_key": api_key, "query": query, "language": language}
    )
    wanted = _bare(query)
    matches = [
        r
        for r in data.get("results") or []
        if any(_bare(r.get(k)).startswith(wanted) for k in ("name", "original_name"))
    ]
    if not matches:
        return None
    best = min(matches, key=lambda r: len(r.get("name") or ""))
    return TmdbMatch("collection", best["id"], best.get("overview") or "")


async def async_tv_seasons(
    session: aiohttp.ClientSession, api_key: str, tv_id: int, language: str
) -> list[dict[str, Any]]:
    """Seasons of a series (specials excluded) with their first air date."""
    data = await _get(session, f"/tv/{tv_id}", {"api_key": api_key, "language": language})
    return [
        {"season": s["season_number"], "air_date": s.get("air_date") or ""}
        for s in data.get("seasons") or []
        if s.get("season_number")
    ]


async def async_movie_collection(
    session: aiohttp.ClientSession, api_key: str, title: str, language: str
) -> int | None:
    """ID of the collection the best movie match for a title belongs to."""
    match = await async_search_movie(session, api_key, title, None, language)
    if match is None:
        return None
    data = await _get(session, f"/movie/{match.id}", {"api_key": api_key, "language": language})
    return (data.get("belongs_to_collection") or {}).get("id")


async def async_collection_parts(
    session: aiohttp.ClientSession, api_key: str, collection_id: int, language: str
) -> list[dict[str, Any]]:
    """Films of a TMDB collection, oldest first."""
    data = await _get(session, f"/collection/{collection_id}", {"api_key": api_key, "language": language})
    parts = []
    for part in data.get("parts") or []:
        date = part.get("release_date") or ""
        parts.append(
            {
                "id": part["id"],
                "title": part.get("title") or "",
                "original_title": part.get("original_title") or "",
                "release_date": date,
                "year": int(date[:4]) if date[:4].isdigit() else None,
                "poster": part.get("poster_path") or "",
                "overview": part.get("overview") or "",
            }
        )
    return sorted(parts, key=lambda p: p["release_date"] or "9999")


async def async_posters(
    session: aiohttp.ClientSession, api_key: str, match: TmdbMatch, language: str
) -> list[dict[str, Any]]:
    """All posters of a movie, series or collection, with their size and language."""
    path = f"/{match.kind}/{match.id}"
    if match.kind == "tv" and match.season:
        path += f"/season/{match.season}"
    data = await _get(
        session, f"{path}/images", {"api_key": api_key, "include_image_language": f"{language},null,en"}
    )
    return [
        {
            "path": p["file_path"],
            "width": p.get("width") or 0,
            "height": p.get("height") or 0,
            "lang": p.get("iso_639_1"),
            "votes": p.get("vote_average") or 0,
        }
        for p in data.get("posters") or []
        if p.get("file_path")
    ]


_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "premiere": 1, "deuxieme": 2, "seconde": 2,
    "troisieme": 3, "quatrieme": 4, "cinquieme": 5, "sixieme": 6, "septieme": 7,
    "huitieme": 8, "neuvieme": 9, "dixieme": 10,
}
_SEASON_NUMBER = re.compile(r"\b(?:season|saison|staffel|temporada|stagione)\s*(\d{1,2})\b|\bs(\d{1,2})\b")
_SEASON_WORD = re.compile(r"\b(\w+)\s+(?:season|saison)\b")


def season_number(title: str) -> int | None:
    """'Dark Angel: The Complete Second Season' -> 2; None when no season is named."""
    text = normalize_title(title)
    if match := _SEASON_NUMBER.search(text):
        return int(match.group(1) or match.group(2))
    for match in _SEASON_WORD.finditer(text):
        if match.group(1) in _ORDINALS:
            return _ORDINALS[match.group(1)]
    return None


def rank_posters(posters: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    """Sharp posters (≥ 1000 px wide) first; then the user's language, textless, English."""
    rank = {language: 0, None: 1, "en": 2}
    return sorted(
        posters,
        key=lambda p: (p["width"] < GOOD_WIDTH, rank.get(p["lang"], 3), -p["votes"], -p["width"]),
    )


def best_poster(posters: list[dict[str, Any]], language: str) -> dict[str, Any] | None:
    """The poster shown when the user did not choose one."""
    ranked = rank_posters(posters, language)
    return ranked[0] if ranked else None
