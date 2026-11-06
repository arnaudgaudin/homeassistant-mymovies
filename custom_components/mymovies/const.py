"""Constants for the My Movies integration."""

from datetime import timedelta

DOMAIN = "mymovies"
UPDATE_INTERVAL = timedelta(hours=1)
STORAGE_VERSION = 1

# My Movies closed its API to third-party apps on 2026-11-04. The API code is kept but
# switched off: the collection comes from the CSV export and TMDB. Set back to True if
# My Movies grants access again (sign-in, watched writes and the panel buttons return).
API_ENABLED = False


def api_enabled() -> bool:
    """Whether the My Movies API is used (read at call time, so tests can switch it)."""
    return API_ENABLED


CONF_EXPORT_FILE = "export_file"
CONF_TMDB_API_KEY = "tmdb_api_key"
CONF_OMDB_API_KEY = "omdb_api_key"
# Where to get the keys, shown in the setup and options forms.
KEY_URLS = {
    "tmdb_url": "https://www.themoviedb.org/settings/api",
    "omdb_url": "https://www.omdbapi.com/apikey.aspx",
}

ATTR_TITLE = "title"
ATTR_NOTES = "notes"

TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w342"

PANEL_URL = "mymovies"
STATIC_URL = "/mymovies_static"
THUMBNAIL_PATH = "/api/mymovies/thumbnail/{entry_id}/{title_id}"
COVER_PATH = "/api/mymovies/cover/{entry_id}/{key}"
MYMOVIES_THUMBNAIL = (100, 138)  # size of the API cover thumbnails
THUMBNAIL_URL_LIFETIME = timedelta(hours=24)
