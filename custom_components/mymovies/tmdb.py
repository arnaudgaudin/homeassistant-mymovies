"""Optional TMDB lookup of posters by IMDb ID (needs a free TMDB API key)."""

from __future__ import annotations

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
