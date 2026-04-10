"""Binary sensor platform for the Segway PowerCube integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerCubeCoordinator
from .entity import PowerCubeEntity


@dataclass(frozen=True, kw_only=True)
class PowerCubeBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a PowerCube binary sensor."""
    value_fn: Any = None


BINARY_SENSORS: tuple[PowerCubeBinarySensorDescription, ...] = (
    PowerCubeBinarySensorDescription(
        key="is_charging",
        translation_key="is_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda d: d["status"]["is_charging"],
    ),
    PowerCubeBinarySensorDescription(
        key="has_errors",
        translation_key="has_errors",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: bool(d["errors"]["errors"]),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerCubeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PowerCubeBinarySensor(coordinator, desc) for desc in BINARY_SENSORS
    )


class PowerCubeBinarySensor(PowerCubeEntity, BinarySensorEntity):
    """A binary sensor entity for the PowerCube."""

    entity_description: PowerCubeBinarySensorDescription

    def __init__(
        self,
        coordinator: PowerCubeCoordinator,
        description: PowerCubeBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        try:
            return bool(self.entity_description.value_fn(self.coordinator.data))
        except (KeyError, TypeError):
            return None
