"""DataUpdateCoordinator for the Segway PowerCube integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from bleak_retry_connector import establish_connection, BleakClientWithServiceCache

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from powercube.client import PowerCube, PowerCubeError
from .const import DOMAIN, BMS_POLL_INTERVAL, FAST_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PowerCubeCoordinator(DataUpdateCoordinator):
    """Manages a persistent BLE connection and periodic data refresh."""

    def __init__(
        self,
        hass: HomeAssistant,
        address: str,
        ble_name: str,
        mkey_pwd: bytes,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=FAST_POLL_INTERVAL),
        )
        self._address = address
        self._ble_name = ble_name
        self._mkey_pwd = mkey_pwd
        self._cube: PowerCube | None = None
        self._bms_tick = 0

    def _get_ble_device(self):
        return bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )

    async def _ensure_connected(self) -> PowerCube:
        if self._cube is not None and self._cube.is_connected:
            # Refresh the BLEDevice so bleak uses the freshest adapter/proxy path
            ble_device = self._get_ble_device()
            if ble_device is not None:
                self._cube.update_ble_device(ble_device)
            return self._cube

        # Tear down any stale connection
        if self._cube is not None:
            try:
                await self._cube.disconnect()
            except Exception:
                pass
            self._cube = None

        ble_device = self._get_ble_device()
        if ble_device is None:
            raise UpdateFailed(f"PowerCube {self._address} not found in range")

        cube = PowerCube(
            ble_device,
            ble_name=self._ble_name,
            mkey_pwd=self._mkey_pwd,
        )

        # Use establish_connection so bleak_retry_connector handles retries
        # and selects the best adapter or ESPHome Bluetooth proxy automatically.
        bleak_client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self._address,
        )

        # Hand the connected client to PowerCube to run the Ninebot handshake
        await cube._handshake_with_client(bleak_client)
        self._cube = cube
        return cube

    async def _async_update_data(self) -> dict:
        try:
            cube = await self._ensure_connected()

            status = await cube.get_status()
            output_info = await cube.get_output_info()
            settings = await cube.get_settings()
            temps = await cube.get_temperatures()
            errors = await cube.get_errors()

            bms_data: dict[int, dict] = {}
            self._bms_tick += 1
            if self._bms_tick * FAST_POLL_INTERVAL >= BMS_POLL_INTERVAL:
                self._bms_tick = 0
                device_info = await cube.get_device_info()
                bms_count = device_info.get("bms_count", 0)
                for i in range(1, bms_count + 1):
                    try:
                        bms_data[i] = await cube.get_bms_info(i)
                    except (PowerCubeError, asyncio.TimeoutError):
                        _LOGGER.debug("BMS %d poll failed", i)

            return {
                "status": status,
                "output_info": output_info,
                "settings": settings,
                "temps": temps,
                "errors": errors,
                "bms": bms_data or (self.data.get("bms", {}) if self.data else {}),
            }

        except (PowerCubeError, asyncio.TimeoutError, OSError) as err:
            if self._cube is not None:
                try:
                    await self._cube.disconnect()
                except Exception:
                    pass
                self._cube = None
            raise UpdateFailed(f"PowerCube communication error: {err}") from err

    async def async_shutdown(self) -> None:
        """Disconnect on unload."""
        if self._cube is not None:
            try:
                await self._cube.disconnect()
            except Exception:
                pass
            self._cube = None
        await super().async_shutdown()
