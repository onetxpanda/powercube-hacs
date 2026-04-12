"""Switch platform for the Segway PowerCube integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerCubeCoordinator
from .entity import PowerCubeEntity


@dataclass(frozen=True, kw_only=True)
class PowerCubeSwitchDescription(SwitchEntityDescription):
    """Describes a PowerCube switch."""
    value_fn: Any = None
    set_fn: Any = None


SWITCHES: tuple[PowerCubeSwitchDescription, ...] = (
    PowerCubeSwitchDescription(
        key="ac_output",
        translation_key="ac_output",
        value_fn=lambda d: d["status"]["ac_output"],
        set_fn=lambda cube, v: cube.set_ac_output(v),
    ),
    PowerCubeSwitchDescription(
        key="dc_output",
        translation_key="dc_output",
        value_fn=lambda d: d["status"]["dc_output"],
        set_fn=lambda cube, v: cube.set_dc_output(v),
    ),
    PowerCubeSwitchDescription(
        key="ups_mode",
        translation_key="ups_mode",
        value_fn=lambda d: d["settings"]["ups_mode"],
        set_fn=lambda cube, v: cube.set_ups_mode(v),
    ),
    PowerCubeSwitchDescription(
        key="super_power",
        translation_key="super_power",
        value_fn=lambda d: d["settings"]["super_power_drive"],
        set_fn=lambda cube, v: cube.set_super_power(v),
    ),
    PowerCubeSwitchDescription(
        key="key_tone",
        translation_key="key_tone",
        value_fn=lambda d: d["settings"]["key_tone"],
        set_fn=lambda cube, v: cube.set_key_tone(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerCubeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PowerCubeSwitch(coordinator, desc) for desc in SWITCHES)


class PowerCubeSwitch(PowerCubeEntity, SwitchEntity):
    """A switch entity for the PowerCube."""

    entity_description: PowerCubeSwitchDescription

    def __init__(
        self,
        coordinator: PowerCubeCoordinator,
        description: PowerCubeSwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is not None:
            try:
                self._attr_is_on = bool(self.entity_description.value_fn(self.coordinator.data))
            except (KeyError, TypeError):
                self._attr_is_on = None
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        cube = self.coordinator._cube
        if cube is None:
            return
        self._attr_is_on = True
        self.async_write_ha_state()
        await self.entity_description.set_fn(cube, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        cube = self.coordinator._cube
        if cube is None:
            return
        self._attr_is_on = False
        self.async_write_ha_state()
        await self.entity_description.set_fn(cube, False)
