# Z-Wave Exporter Project Context

## Hardware
- Zooz 800 Z-Wave USB dongle — `/dev/serial/by-id/usb-Zooz_800_Z-Wave_Stick_533D004242-if00` → `/dev/ttyACM0`
- Aeotec aërQ (ZWA039) temperature/humidity sensor (node 9, insecure inclusion)
- Running on Linux (migrated from macOS)

## Architecture
- `zwave-js-ui` container drives the USB dongle directly (USB passthrough works natively on Linux)
- `zwave-exporter` Python container connects via WebSocket to `ws://zwave-js-ui:3000` (same Docker network)
- Prometheus metrics served on :9100

## Current status
- Sensor paired and working as node 9 (insecure inclusion, no S2)
- Exporter publishing: `zwave_temperature_celsius`, `zwave_humidity_percent`, `zwave_dew_point_celsius`, `zwave_node_alive`, `zwave_node_battery_level`, `zwave_node_info`
- Wakeup interval: 3600 seconds (1 hour) — sensor self-reports on this interval
- Migrated from macOS to Linux — full docker compose stack

## Run commands

### macOS dev (for reference — zwave-js-server native, exporter in Docker)
```
zwave-server /dev/cu.usbserial-533D0042421 --port 3000
docker compose run --no-deps --rm --build -e ZWAVE_WS_URL=ws://host.docker.internal:3000 --service-ports zwave-exporter python exporter.py
```

### Pairing / management tool
```
docker compose run --no-deps --rm -e ZWAVE_WS_URL=ws://host.docker.internal:3000 zwave-exporter python pair.py
```

### Linux (full docker compose, USB passthrough works natively)
```
docker compose up
```

## Key issues solved
- Docker Desktop/Rancher Desktop can't pass USB to containers on macOS — use npx native server
- `client.connect()` takes no args in zwave-js-server-python 0.63.0
- `client.driver` is None immediately after `connect()` — must run `client.listen()` as background task and poll for driver_ready event
- S2 security bootstrapping always fails for this sensor with `InclusionStrategy.DEFAULT` — use `InclusionStrategy.INSECURE` (option 2i in pair.py)
- `Value.command_class_id` does not exist — correct attribute is `Value.command_class`
- `Value.property` is a reserved word — correct attribute is `Value.property_` (trailing underscore)
- Multilevel Sensor `property_` is a **string** (`"Air temperature"`, `"Humidity"`, `"Dew point"`), not a numeric sensor type code — matching against integers will silently fail
- Triple-pressing the tamper button sends a Node Info Frame (NIF), not a WakeUp Notification — the sensor only sends temperature/humidity data with its scheduled `WakeUpCCWakeUpNotification`

## pair.py menu options
| Option | Action |
|--------|--------|
| 1 | List nodes |
| 2 | Include (pair) — S2/S0, usually fails for ZWA039 |
| 2i | Include insecure — use this for ZWA039 |
| 3 | Exclude (unpair) |
| 4 | Dump values for a node |
| 5 | Heal network |
| 6 | Re-interview a node |
| 7 | Force-remove a failed node |
| 8 | Watch node & refresh on wakeup |
| 9 | Interview node on next wakeup |
| w | Set wakeup interval (seconds) |

## Sensor config (ZWA039 node 9)
- Config param 4: Automatic Reporting Interval (seconds) — currently 43200 default, set to 3600 via pair.py option w
- Config param 64: Temperature unit — value 2 = Fahrenheit (sensor reports in °F, exporter converts to °C)
- Wakeup interval (CC 132, property wakeUpInterval): 3600 seconds

## Linux deployment notes
- USB device will be `/dev/ttyUSB0` or `/dev/ttyACM0` — check with `ls /dev/tty*` after plugging in dongle
- docker-compose.yml already has USB device passthrough configured for Linux
- zwave-js state cache is in `./cache/` — copy this directory to the Linux host along with the rest of the repo to avoid re-pairing the sensor
- The cache home ID is `f3c91f96` (hex for home ID 4090044310)
