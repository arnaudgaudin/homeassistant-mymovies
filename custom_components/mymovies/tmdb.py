"""Optional TMDB lookup of posters by IMDb ID (needs a free TMDB API key)."""

from __future__ import annotations

import re

import aiohttp

TMDB_API = "https://api.themoviedb.org/3"
TIMEOUT = aiohttp.ClientTimeout(total=20)


class TmdbError(Exception):
    """TMDB could not be reached or answered unexpectedly."""


class TmdbAuthError(TmdbError):
    """TMDB rejected the API key."""


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


async def async_find_poster(session: aiohttp.ClientSession, api_key: str, imdb: str) -> str:
    """Poster path of the movie or series with this IMDb ID ("" when none)."""
    data = await _get(
        session, f"/find/{imdb}", {"api_key": api_key, "external_source": "imdb_id"}
    )
    for kind in ("movie_results", "tv_results"):
        for result in data.get(kind) or []:
            if result.get("poster_path"):
                return result["poster_path"]
    return ""


async def async_search_movie(
    session: aiohttp.ClientSession, api_key: str, title: str, year: int | None, language: str
) -> dict[str, str]:
    """Poster path and synopsis of the best match for a title ("" when none)."""
    params = {"api_key": api_key, "query": title, "language": language}
    if year:
        params["year"] = str(year)
    data = await _get(session, "/search/movie", params)
    for result in data.get("results") or []:
        return {"poster": result.get("poster_path") or "", "overview": result.get("overview") or ""}
    return {"poster": "", "overview": ""}


# Words of box-set titles that are not part of the franchise name.
_BOX_SET_NOISE = re.compile(
    r"(trilog(y|ie)|int[ée]grale|collection|coffret|saga|\d+\s*films?|"
    r"l[’']?[ée]dition.*|[ée]dition.*|anniversa\w*.*|box\s*set)",
    re.IGNORECASE,
)


def franchise_name(title: str) -> str:
    """'Harry Potter: L'Édition Anniversaire Collector' -> 'Harry Potter'."""
    name = _BOX_SET_NOISE.sub(" ", title)
    return re.sub(r"\s+", " ", name).strip(" :-–—")


async def async_search_collection(
    session: aiohttp.ClientSession, api_key: str, title: str, language: str
) -> str:
    """Poster path of the TMDB collection matching a box-set title ("" when none)."""
    query = franchise_name(title)
    if not query:
        return ""
    data = await _get(
        session, "/search/collection", {"api_key": api_key, "query": query, "language": language}
    )
    for result in data.get("results") or []:
        if result.get("poster_path"):
            return result["poster_path"]
    return ""
