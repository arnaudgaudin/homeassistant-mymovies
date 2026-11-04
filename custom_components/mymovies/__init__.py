"""The My Movies integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import DATA_PANELS, async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .api import MyMoviesClient
from .catalog import CatalogStore
from .const import DOMAIN, PANEL_URL, STATIC_URL
from .coordinator import MyMoviesConfigEntry, MyMoviesCoordinator
from .services import async_setup_services
from .covers import remove_entry_uploads
from .views import MyMoviesCoverView, MyMoviesThumbnailView
from .websocket import async_setup_websocket

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register services, the thumbnail view, the panel API and its files once."""
    async_setup_services(hass)
    async_setup_websocket(hass)
    hass.http.register_view(MyMoviesThumbnailView(hass))
    hass.http.register_view(MyMoviesCoverView(hass))
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
    )
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
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_panel(hass)
    return True


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Add the "My Movies" sidebar panel (once for all accounts)."""
    if PANEL_URL in hass.data.get(DATA_PANELS, {}):
        return
    version = (await async_get_integration(hass, DOMAIN)).version
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name="mymovies-panel",
        sidebar_title="My Movies",
        sidebar_icon="mdi:filmstrip-box-multiple",
        module_url=f"{STATIC_URL}/mymovies-panel.js?v={version}",
        require_admin=False,
    )


async def _async_reload(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> None:
    """Apply new options (export, TMDB key)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> bool:
    """Unload one My Movies account; drop the panel with the last one."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    others = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
    ]
    if unloaded and not others:
        async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: MyMoviesConfigEntry) -> None:
    """Delete the stored catalog and the uploaded covers of a removed account."""
    await CatalogStore(hass, entry.entry_id).async_remove()
    await hass.async_add_executor_job(remove_entry_uploads, hass, entry.entry_id)
