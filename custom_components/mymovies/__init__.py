"""The My Movies integration."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import MyMoviesClient
from .catalog import CatalogStore
from .const import DOMAIN
from .coordinator import MyMoviesConfigEntry, MyMoviesCoordinator
from .services import async_setup_services
from .views import MyMoviesThumbnailView

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services and the thumbnail view once."""
    async_setup_services(hass)
    hass.http.register_view(MyMoviesThumbnailView(hass))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> bool:
    """Set up one My Movies account."""
    client = MyMoviesClient(
        async_get_clientsession(hass), entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    store = CatalogStore(hass, entry.entry_id)
    await store.async_load()
    coordinator = MyMoviesCoordinator(hass, entry, client, store)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    entry.async_create_background_task(
        hass, coordinator.async_fetch_posters(), f"{DOMAIN}_posters_{entry.entry_id}"
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> None:
    """Apply new options (TMDB key)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> bool:
    """Unload one My Movies account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> None:
    """Delete the stored catalog of a removed account."""
    await CatalogStore(hass, entry.entry_id).async_remove()
