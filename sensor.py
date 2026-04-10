"""Sensor platform for the Segway PowerCube integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import PowerCubeCoordinator
from .entity import PowerCubeEntity


@dataclass(frozen=True, kw_only=True)
class PowerCubeSensorDescription(SensorEntityDescription):
    """Describes a PowerCube sensor."""
    value_fn: Any = None


# ── Main status sensors ───────────────────────────────────────────────────────

STATUS_SENSORS: tuple[PowerCubeSensorDescription, ...] = (
    PowerCubeSensorDescription(
        key="soc_pct",
        translation_key="soc_pct",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["status"]["soc_pct"],
    ),
    PowerCubeSensorDescription(
        key="temp_c",
        translation_key="temp_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["status"]["temp_c"],
    ),
    PowerCubeSensorDescription(
        key="capacity_wh",
        translation_key="capacity_wh",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["status"]["capacity_wh"],
    ),
    PowerCubeSensorDescription(
        key="input_power_w",
        translation_key="input_power_w",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["status"]["input_power_w"],
    ),
    PowerCubeSensorDescription(
        key="output_power_w",
        translation_key="output_power_w",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["status"]["output_power_w"],
    ),
    PowerCubeSensorDescription(
        key="remain_time_min",
        translation_key="remain_time_min",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["status"]["remain_time_min"],
    ),
)

# ── Temperature sensors ───────────────────────────────────────────────────────

TEMP_SENSOR_KEYS = [
    "mcu", "mcu_2", "bms", "bms_2",
    "ac_inv", "ac_inv_2", "dc_conv", "dc_conv_2",
    "pv_input", "pv_input_2",
]

TEMP_SENSORS: tuple[PowerCubeSensorDescription, ...] = tuple(
    PowerCubeSensorDescription(
        key=f"temp_{name}",
        translation_key=f"temp_{name}",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=(lambda n: lambda d: d["temps"].get(n))(name),
    )
    for name in TEMP_SENSOR_KEYS
)

# ── Per-port output sensors ───────────────────────────────────────────────────

OUTPUT_PORTS = ["usb_c1", "usb_c2", "usb_a1", "usb_a2", "usb_a3", "usb_a4", "dc", "ac"]

OUTPUT_SENSORS: tuple[PowerCubeSensorDescription, ...] = tuple(
    sensor
    for port in OUTPUT_PORTS
    for sensor in (
        PowerCubeSensorDescription(
            key=f"port_{port}_power_w",
            translation_key=f"port_{port}_power_w",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=(port in ("ac", "dc")),
            value_fn=(lambda p: lambda d: d["output_info"].get(p, {}).get("power_w"))(port),
        ),
        PowerCubeSensorDescription(
            key=f"port_{port}_voltage_v",
            translation_key=f"port_{port}_voltage_v",
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
            value_fn=(lambda p: lambda d: d["output_info"].get(p, {}).get("voltage_v"))(port),
        ),
        PowerCubeSensorDescription(
            key=f"port_{port}_current_a",
            translation_key=f"port_{port}_current_a",
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=False,
            value_fn=(lambda p: lambda d: d["output_info"].get(p, {}).get("current_a"))(port),
        ),
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PowerCubeCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[PowerCubeSensor] = []

    for desc in (*STATUS_SENSORS, *TEMP_SENSORS, *OUTPUT_SENSORS):
        entities.append(PowerCubeSensor(coordinator, desc))

    async_add_entities(entities)

    # BMS sensors are added dynamically after first BMS poll
    def _add_bms_sensors() -> None:
        bms_data: dict = coordinator.data.get("bms", {}) if coordinator.data else {}
        new_entities = []
        for bms_num in bms_data:
            for desc in _bms_sensor_descriptions(bms_num):
                new_entities.append(PowerCubeSensor(coordinator, desc))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(
        coordinator.async_add_listener(lambda: _add_bms_sensors() if coordinator.data and coordinator.data.get("bms") else None)
    )


def _bms_sensor_descriptions(bms_num: int) -> list[PowerCubeSensorDescription]:
    n = bms_num
    return [
        PowerCubeSensorDescription(
            key=f"bms{n}_cycle_count",
            translation_key="bms_cycle_count",
            state_class=SensorStateClass.TOTAL_INCREASING,
            value_fn=(lambda i: lambda d: d["bms"].get(i, {}).get("cycle_count"))(n),
        ),
        PowerCubeSensorDescription(
            key=f"bms{n}_pack_voltage_mv",
            translation_key="bms_pack_voltage",
            native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
            device_class=SensorDeviceClass.VOLTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=(lambda i: lambda d: d["bms"].get(i, {}).get("pack_voltage_mv"))(n),
        ),
        PowerCubeSensorDescription(
            key=f"bms{n}_current_ma",
            translation_key="bms_current",
            native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
            device_class=SensorDeviceClass.CURRENT,
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=(lambda i: lambda d: d["bms"].get(i, {}).get("current_ma"))(n),
        ),
    ]


class PowerCubeSensor(PowerCubeEntity, SensorEntity):
    """A sensor entity for the PowerCube."""

    entity_description: PowerCubeSensorDescription

    def __init__(
        self,
        coordinator: PowerCubeCoordinator,
        description: PowerCubeSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except (KeyError, TypeError):
            return None
