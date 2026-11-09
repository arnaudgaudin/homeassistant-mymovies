"""OMDb (IMDb data) lookups: a fallback for what TMDB leaves empty."""

from __future__ import annotations

from typing import Any

import aiohttp

OMDB_API = "https://www.omdbapi.com/"
TIMEOUT = aiohttp.ClientTimeout(total=15)

# IMDb genres as the English genre names of My Movies (others are left out).
GENRES = {
    "Sci-Fi": "Science-Fiction", "Thriller": "Suspense/Thriller", "Action": "Action",
    "Adventure": "Adventure", "Animation": "Animation", "Biography": "Biography",
    "Comedy": "Comedy", "Crime": "Crime", "Documentary": "Documentary", "Drama": "Drama",
    "Family": "Family", "Fantasy": "Fantasy", "Film-Noir": "Film-Noir", "History": "History",
    "Horror": "Horror", "Music": "Music", "Musical": "Musical", "Mystery": "Mystery",
    "Romance": "Romance", "Sport": "Sport", "War": "War", "Western": "Western",
}

# OMDb gives country names: the usual film countries as ISO 3166-1 codes.
# ponytail: a fixed list, unknown names are skipped; add a name when one shows up missing.
COUNTRIES = {
    "United States": "US", "USA": "US", "United Kingdom": "GB", "UK": "GB", "France": "FR",
    "Germany": "DE", "West Germany": "DE", "Italy": "IT", "Spain": "ES", "Canada": "CA",
    "Australia": "AU", "New Zealand": "NZ", "Japan": "JP", "South Korea": "KR", "China": "CN",
    "Hong Kong": "HK", "Taiwan": "TW", "India": "IN", "Belgium": "BE", "Netherlands": "NL",
    "Luxembourg": "LU", "Switzerland": "CH", "Austria": "AT", "Ireland": "IE", "Denmark": "DK",
    "Sweden": "SE", "Norway": "NO", "Finland": "FI", "Iceland": "IS", "Poland": "PL",
    "Czech Republic": "CZ", "Czechia": "CZ", "Hungary": "HU", "Russia": "RU", "Mexico": "MX",
    "Brazil": "BR", "Argentina": "AR", "South Africa": "ZA", "Morocco": "MA", "Malta": "MT",
    "United Arab Emirates": "AE", "Thailand": "TH", "Greece": "GR", "Portugal": "PT",
    "Bulgaria": "BG", "Romania": "RO", "Israel": "IL", "Turkey": "TR",
}


class OmdbError(Exception):
    """OMDb could not be reached or refused the request."""


class OmdbAuthError(OmdbError):
    """The key is invalid or its daily limit is reached."""


async def _get(session: aiohttp.ClientSession, params: dict[str, str]) -> dict[str, Any] | None:
    try:
        async with session.get(OMDB_API, params=params, timeout=TIMEOUT) as resp:
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError, ValueError) as err:
        # A timeout has no message: name it rather than log an empty reason
        raise OmdbError(str(err) or type(err).__name__) from err
    if data.get("Response") == "True":
        return data
    error = data.get("Error", "")
    if "key" in error.lower() or "limit" in error.lower():
        raise OmdbAuthError(error)
    return None  # not found


async def async_validate_key(session: aiohttp.ClientSession, api_key: str) -> None:
    """Raise OmdbAuthError when the key is not accepted."""
    await _get(session, {"apikey": api_key, "i": "tt0133093"})


def _value(data: dict[str, Any], name: str) -> str:
    value = data.get(name) or ""
    return "" if value == "N/A" else value


def _names(value: str) -> list[str]:
    return [n.strip() for n in value.split(",") if n.strip()]


def parse(data: dict[str, Any]) -> dict[str, Any]:
    """The fields used to complete a title: rating, genres, countries, runtime, director."""
    rating = _value(data, "imdbRating")
    runtime = _value(data, "Runtime").split(" ")[0]
    return {
        "rating": float(rating) if rating.replace(".", "", 1).isdigit() else None,
        "genres": list(dict.fromkeys(GENRES[g] for g in _names(_value(data, "Genre")) if g in GENRES)),
        "countries": list(
            dict.fromkeys(COUNTRIES[c] for c in _names(_value(data, "Country")) if c in COUNTRIES)
        ),
        "runtime": int(runtime) if runtime.isdigit() else None,
        "director": _value(data, "Director"),
    }


async def async_lookup(
    session: aiohttp.ClientSession, api_key: str, *, imdb: str | None, title: str, year: int | None
) -> dict[str, Any]:
    """A title by IMDb ID, else by title and year; {} when OMDb does not know it."""
    params = {"apikey": api_key, "i": imdb} if imdb else {"apikey": api_key, "t": title}
    if not imdb and year:
        params["y"] = str(year)
    data = await _get(session, params)
    return parse(data) if data else {}
