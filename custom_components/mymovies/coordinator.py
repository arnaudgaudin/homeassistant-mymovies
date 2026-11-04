"""Data update coordinator for the My Movies integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CollectionTitle, MyMoviesAuthError, MyMoviesClient, MyMoviesError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type MyMoviesConfigEntry = ConfigEntry[MyMoviesCoordinator]


@dataclass(slots=True)
class MyMoviesData:
    """Collection snapshot: titles keyed by their lower-case ID."""

    titles: dict[str, CollectionTitle]


class MyMoviesCoordinator(DataUpdateCoordinator[MyMoviesData]):
    """Poll the collection and its watched flags."""

    config_entry: MyMoviesConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: MyMoviesConfigEntry, client: MyMoviesClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> MyMoviesData:
        try:
            titles = await self.client.async_get_titles()
        except MyMoviesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except MyMoviesError as err:
            raise UpdateFailed(str(err)) from err
        return MyMoviesData(titles={t.id.lower(): t for t in titles})
