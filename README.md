# Segway PowerCube — Home Assistant Integration

[HACS](https://hacs.xyz/) integration for controlling the **Segway PowerCube** portable power station from Home Assistant over Bluetooth LE.

## Prerequisites

- Home Assistant 2024.1 or newer
- [HACS](https://hacs.xyz/) installed
- A Bluetooth adapter accessible by Home Assistant (built-in or USB dongle)

## Installation

1. In HACS, add `onetxpanda/powercube-hacs` as a **custom repository** (category: Integration).
2. Install **Segway PowerCube**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for *PowerCube*.

When the device is in range, Home Assistant will detect it automatically via Bluetooth.

## Pairing

If the device has never been paired, you will be prompted to press the power button on the PowerCube to confirm pairing. If it has been paired before, enter the key from your existing credentials file (`~/.config/powercube/<address>.json`).

## Entities

| Platform | Entity | Description |
|---|---|---|
| Sensor | Battery | State of charge (%) |
| Sensor | Capacity | Current battery capacity (Wh) |
| Sensor | Input Power | Total power in (W) |
| Sensor | Output Power | Total power out (W) |
| Sensor | Temperature | Internal temperature (°C) |
| Sensor | AC/DC Port Power | Per-port power (W) |
| Binary Sensor | Charging | AC input active |
| Binary Sensor | Fault | Any active error condition |
| Switch | AC Output | Toggle AC outlet |
| Switch | DC Output | Toggle DC 12V port |
| Switch | UPS Mode | Uninterruptible power mode |
| Switch | Super Power Drive | Enhanced inverter mode |
| Switch | Button Tone | Button press beep |
| Number | AC Input Limit | AC charging power cap (W) |
| Number | Standby Timers | AC/DC/device auto-off times |
| Select | AC Frequency | 50 Hz / 60 Hz |

## License

MIT
