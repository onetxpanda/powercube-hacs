"""Number platform for the Segway PowerCube integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerCubeCoordinator
from .entity import PowerCubeEntity


@dataclass(frozen=True, kw_only=True)
class PowerCubeNumberDescription(NumberEntityDescription):
    """Describes a PowerCube number."""
    value_fn: Any = None
    set_fn: Any = None


NUMBERS: tuple[PowerCubeNumberDescription, ...] = (
    PowerCubeNumberDescription(
        key="ac_input_limit_w",
        translation_key="ac_input_limit_w",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=NumberDeviceClass.POWER,
        mode=NumberMode.BOX,
        native_min_value=100,
        native_max_value=1650,
        native_step=50,
        value_fn=lambda d: d["settings"]["ac_input_limit_w"],
        set_fn=lambda cube, v: cube.set_ac_input_limit(int(v)),
    ),
    PowerCubeNumberDescription(
        key="ac_standby_min",
        translation_key="ac_standby_min",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        value_fn=lambda d: d["settings"]["ac_standby_min"],
        set_fn=lambda cube, v: cube.set_ac_standby(int(v)),
    ),
    PowerCubeNumberDescription(
        key="dc_standby_min",
        translation_key="dc_standby_min",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        value_fn=lambda d: d["settings"]["dc_standby_min"],
        set_fn=lambda cube, v: cube.set_dc_standby(int(v)),
    ),
    PowerCubeNumberDescription(
        key="device_standby_min",
        translation_key="device_standby_min",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=1440,
        native_step=1,
        value_fn=lambda d: d["settings"]["device_standby_min"],
        set_fn=lambda cube, v: cube.set_device_standby(int(v)),
    ),
    PowerCubeNumberDescription(
        key="screen_time_min",
        translation_key="screen_time_min",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        native_min_value=0,
        native_max_value=60,
        native_step=1,
        value_fn=lambda d: d["settings"]["screen_time_min"],
        set_fn=lambda cube, v: cube.set_screen_time(int(v)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerCubeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PowerCubeNumber(coordinator, desc) for desc in NUMBERS)


class PowerCubeNumber(PowerCubeEntity, NumberEntity):
    """A number entity for the PowerCube."""

    entity_description: PowerCubeNumberDescription

    def __init__(
        self,
        coordinator: PowerCubeCoordinator,
        description: PowerCubeNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        try:
            return float(self.entity_description.value_fn(self.coordinator.data))
        except (KeyError, TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        cube = self.coordinator._cube
        if cube is None:
            return
        await self.entity_description.set_fn(cube, value)
        await self.coordinator.async_request_refresh()
