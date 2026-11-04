"""Constants for the My Movies integration."""

from datetime import timedelta

DOMAIN = "mymovies"
UPDATE_INTERVAL = timedelta(hours=1)
STORAGE_VERSION = 1

CONF_EXPORT_FILE = "export_file"
CONF_TMDB_API_KEY = "tmdb_api_key"

ATTR_TITLE = "title"
ATTR_NOTES = "notes"

TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w342"

PANEL_URL = "mymovies"
STATIC_URL = "/mymovies_static"
THUMBNAIL_PATH = "/api/mymovies/thumbnail/{entry_id}/{title_id}"
COVER_PATH = "/api/mymovies/cover/{entry_id}/{key}"
MYMOVIES_THUMBNAIL = (100, 138)  # size of the API cover thumbnails
THUMBNAIL_URL_LIFETIME = timedelta(hours=24)
