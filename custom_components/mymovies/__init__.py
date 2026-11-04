"""The My Movies integration."""

from __future__ import annotations

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import MyMoviesClient
from .const import DOMAIN
from .coordinator import MyMoviesConfigEntry, MyMoviesCoordinator
from .services import async_setup_services

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration's services once."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> bool:
    """Set up one My Movies account."""
    client = MyMoviesClient(
        async_get_clientsession(hass), entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
    )
    coordinator = MyMoviesCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> bool:
    """Unload one My Movies account."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
