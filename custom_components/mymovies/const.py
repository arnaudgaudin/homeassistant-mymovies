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
