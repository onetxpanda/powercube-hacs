"""Config flow for Segway PowerCube."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from powercube.client import PowerCube, PowerCubeError
from powercube.protocol import NOTIFY_UUID
from .const import DOMAIN, CONF_BLE_NAME, CONF_MKEY_PWD, DEFAULT_BLE_NAME

_LOGGER = logging.getLogger(__name__)


class PowerCubeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Segway PowerCube."""

    VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None
        self._ble_name: str = DEFAULT_BLE_NAME
        self._device_has_pwd: bool | None = None  # set by probe task
        self._mkey_pwd: bytes | None = None        # set after successful pairing
        self._probe_task: asyncio.Task | None = None
        self._error: str | None = None

    # ── Bluetooth auto-discovery ──────────────────────────────────────────────

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address
        if discovery_info.name:
            self._ble_name = discovery_info.name
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_probe()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._ble_name,
                "address": self._address,
            },
        )

    # ── Manual address entry ──────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._address = user_input["address"].strip().upper()
            self._ble_name = user_input.get(CONF_BLE_NAME, DEFAULT_BLE_NAME)
            await self.async_set_unique_id(self._address)
            self._abort_if_unique_id_configured()
            return await self.async_step_probe()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("address"): str,
                vol.Optional(CONF_BLE_NAME, default=DEFAULT_BLE_NAME): str,
            }),
            errors=errors,
        )

    # ── Step 1: probe / pair (single background task) ────────────────────────
    #
    # One background task does PRE_COMM first. If the device is unpaired it
    # continues through SET_PWD (button press). If the device is already paired
    # it sets _device_has_pwd=True and exits, and the step routes to enter_key.

    async def async_step_probe(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Connect, detect pairing status, and either pair or ask for the key."""
        if self._error is not None:
            err = self._error
            self._error = None
            return self.async_show_form(
                step_id="probe",
                errors={"base": err},
                description_placeholders={"address": self._address},
            )

        if self._device_has_pwd is True:
            # Device is already paired — ask for the existing key
            return await self.async_step_enter_key()

        if self._mkey_pwd is not None:
            # Button-press pairing completed successfully
            return self.async_create_entry(
                title=f"PowerCube {self._address}",
                data=self._entry_data(self._mkey_pwd),
            )

        return self.async_show_progress(
            step_id="probe",
            progress_action="pairing",
            description_placeholders={"address": self._address},
            progress_task=self._async_start_probe_task(),
        )

    def _async_start_probe_task(self) -> asyncio.Task:
        if self._probe_task is None or self._probe_task.done():
            self._probe_task = self.hass.async_create_task(self._do_probe_and_pair())
        return self._probe_task

    async def _do_probe_and_pair(self) -> None:
        """
        Background task: connect, run PRE_COMM to detect pairing status.

        - If device is unpaired (arg=0): continue with SET_PWD button-press flow.
        - If device is already paired (arg=1): set _device_has_pwd=True and exit
          so the step routes to the key-entry form.
        """
        from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

        cube = self._make_client()
        try:
            ble_device = self._get_ble_device()
            if ble_device is None:
                self._error = "cannot_connect"
                return

            # Use establish_connection so proxy routing and retries are handled
            bleak_client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self._address,
            )

            # Run PRE_COMM only (no auth) to detect pairing status
            cube._client = bleak_client
            await bleak_client.start_notify(NOTIFY_UUID, cube._on_notify)
            await cube._do_pre_comm()

            if cube._device_has_pwd:
                self._device_has_pwd = True
                return

            # Unpaired — continue with SET_PWD on the same connection
            self._device_has_pwd = False
            await cube.pair()
            self._mkey_pwd = cube.get_credential()

        except PowerCubeError as err:
            _LOGGER.error("Probe/pair failed: %s", err)
            self._error = "cannot_connect"
        except Exception as err:
            _LOGGER.exception("Unexpected error during probe/pair: %s", err)
            self._error = "unknown"
        finally:
            try:
                await cube.disconnect()
            except Exception:
                pass
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_configure(flow_id=self.flow_id)
            )

    # ── Step 2: device already paired — ask for the key ──────────────────────

    async def async_step_enter_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the existing mKeyPwd (device is already paired with another app)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            raw = user_input.get(CONF_MKEY_PWD, "").strip().replace(" ", "").replace(":", "")
            if len(raw) != 32:
                errors[CONF_MKEY_PWD] = "invalid_key"
            else:
                try:
                    mkey_pwd = bytes.fromhex(raw)
                except ValueError:
                    errors[CONF_MKEY_PWD] = "invalid_key"
                else:
                    ok, err_key = await self._try_auth(mkey_pwd)
                    if ok:
                        return self.async_create_entry(
                            title=f"PowerCube {self._address}",
                            data=self._entry_data(mkey_pwd),
                        )
                    errors[CONF_MKEY_PWD] = err_key

        return self.async_show_form(
            step_id="enter_key",
            data_schema=vol.Schema({
                vol.Required(CONF_MKEY_PWD): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }),
            description_placeholders={"address": self._address},
            errors=errors,
        )

    async def _try_auth(self, mkey_pwd: bytes) -> tuple[bool, str]:
        """Verify the supplied key by attempting a full connect + AUTH."""
        cube = self._make_client(mkey_pwd=mkey_pwd)
        try:
            async with cube:
                pass  # connect() runs PRE_COMM + AUTH; raises on bad key
            return True, ""
        except PowerCubeError as err:
            _LOGGER.debug("AUTH verification failed: %s", err)
            return False, "auth_failed"
        except Exception:
            return False, "cannot_connect"

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_ble_device(self):
        from homeassistant.components import bluetooth
        return bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )

    def _make_client(self, mkey_pwd: bytes | None = None) -> PowerCube:
        ble_device = self._get_ble_device()
        return PowerCube(
            ble_device if ble_device is not None else self._address,
            ble_name=self._ble_name,
            mkey_pwd=mkey_pwd,
            on_pair_prompt=lambda msg: _LOGGER.info("Pair prompt: %s", msg),
        )

    def _entry_data(self, mkey_pwd: bytes) -> dict:
        return {
            "address": self._address,
            CONF_BLE_NAME: self._ble_name,
            CONF_MKEY_PWD: mkey_pwd.hex(),
        }
