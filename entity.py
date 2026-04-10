"""Base entity class for the Segway PowerCube integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PowerCubeCoordinator


class PowerCubeEntity(CoordinatorEntity[PowerCubeCoordinator]):
    """Base class for all PowerCube entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PowerCubeCoordinator, unique_suffix: str) -> None:
        super().__init__(coordinator)
        address = coordinator._address
        self._attr_unique_id = f"{address}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name="Segway PowerCube",
            manufacturer="Segway",
            model="PowerCube",
        )
