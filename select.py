"""Select platform for the Segway PowerCube integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerCubeCoordinator
from .entity import PowerCubeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerCubeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PowerCubeFrequencySelect(coordinator)])


class PowerCubeFrequencySelect(PowerCubeEntity, SelectEntity):
    """Select entity for AC output frequency (50 / 60 Hz)."""

    _attr_translation_key = "ac_frequency"
    _attr_options = ["50", "60"]

    def __init__(self, coordinator: PowerCubeCoordinator) -> None:
        super().__init__(coordinator, "ac_frequency")

    @property
    def current_option(self) -> str | None:
        if self.coordinator.data is None:
            return None
        hz = self.coordinator.data.get("settings", {}).get("frequency_hz")
        return str(hz) if hz in (50, 60) else None

    async def async_select_option(self, option: str) -> None:
        cube = self.coordinator._cube
        if cube is None:
            return
        await cube.set_ac_frequency(int(option))
        await self.coordinator.async_request_refresh()
