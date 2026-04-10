"""Constants for the Segway PowerCube integration."""

DOMAIN = "powercube"

CONF_BLE_NAME = "ble_name"
CONF_MKEY_PWD = "mkey_pwd"

# Polling intervals (seconds)
FAST_POLL_INTERVAL = 30
BMS_POLL_INTERVAL = 300

# Default BLE device advertised name used as the PRE_COMM crypto seed
DEFAULT_BLE_NAME = "PowerCube"

# NUS service UUID used for Bluetooth discovery matching
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
