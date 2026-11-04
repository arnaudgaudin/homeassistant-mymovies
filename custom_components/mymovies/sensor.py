"""Sensors for the My Movies integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyMoviesConfigEntry, MyMoviesCoordinator, MyMoviesData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class MyMoviesSensorDescription(SensorEntityDescription):
    """Sensor description with the function that reads its value."""

    value_fn: Callable[[MyMoviesData], int]


SENSORS: tuple[MyMoviesSensorDescription, ...] = (
    MyMoviesSensorDescription(
        key="titles",
        translation_key="titles",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.titles),
    ),
    MyMoviesSensorDescription(
        key="watched",
        translation_key="watched",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sum(t.watched for t in data.titles.values()),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyMoviesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add the collection sensors."""
    async_add_entities(MyMoviesSensor(entry.runtime_data, d) for d in SENSORS)


class MyMoviesSensor(CoordinatorEntity[MyMoviesCoordinator], SensorEntity):
    """A count over the collection."""

    _attr_has_entity_name = True
    entity_description: MyMoviesSensorDescription

    def __init__(
        self, coordinator: MyMoviesCoordinator, description: MyMoviesSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        uid = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{uid}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            name=f"My Movies ({entry.title})",
            manufacturer="My Movies",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://themovie.network",
        )

    @property
    def native_value(self) -> int:
        return self.entity_description.value_fn(self.coordinator.data)
