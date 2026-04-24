# Z-Wave Prometheus Exporter

Exports temperature, humidity, and dew point from an **Aeotec aërQ (ZWA039)**
sensor paired to a **Zooz ZST38LR** Z-Wave USB dongle.  Metrics are served in
Prometheus format on `:9100/metrics`.

---

## Architecture

```
[Zooz ZST38LR USB] ─► [zwave-js-ui container]  ─► WebSocket :3000
                              │                          │
                         Web UI :8091            [zwave-exporter]
                       (pairing/debug)                   │
                                                  Prometheus :9100
```

Pairing state (network security keys + node database) lives in a Docker named
volume `zwave-config`.  Once paired locally you export that volume and restore
it at the remote site — no re-pairing needed.

---

## Prerequisites

- Docker + Docker Compose v2
- The Zooz ZST38LR dongle plugged in via USB
- A battery installed in the Aeotec aërQ sensor

---

## Step 1 — Find your dongle's stable device path

```bash
ls -la /dev/serial/by-id/
```
on a mac
```
/dev/cu.usbserial-533D0042421 
```

You'll see something like:
```
lrwxrwxrwx 1 root root 13 Apr 22 10:00 usb-Silicon_Labs_Zooz_ZST10_700_Z-Wave_Stick_XXXXXXXX-if00-port0 -> ../../ttyUSB0
```

Copy the full path (starting with `/dev/serial/by-id/...`).

> **Why not /dev/ttyUSB0?**  That number can change when other USB devices are
> plugged in or after a reboot.  The `by-id` symlink is stable.

---

## Step 2 — Configure environment

```bash
cp .env.example .env
# Edit .env:
#   ZWAVE_DEVICE=/dev/serial/by-id/YOUR_ACTUAL_PATH
#   SESSION_SECRET=some_random_string_here
```

---

## Step 3 — Start the stack

```bash
docker compose up -d
docker compose logs -f   # watch startup
```

Wait until you see `zwave-js-ui` log `"Driver is ready"`.

---

## Step 4 — Pair the aërQ sensor (one-time, do this locally)

### Option A: Web UI (easiest)

1. Open **http://localhost:8091** in your browser.
2. Go to **Control Panel → Actions → Manage Nodes → Include**.
3. Click **Start Inclusion**.
4. On the aërQ sensor: **triple-press the tamper/button** (3× within 1 second).
   - Red+Green LEDs blink = entering pairing mode
   - Solid Green for 1.5s = success
   - Solid Red for 1.5s = failure (try again)
5. The node should appear in the Control Panel within ~30 seconds.

### Option B: pair.py script

```bash
# Run pair.py against the local WS port
docker compose run --rm zwave-exporter python pair.py --url ws://localhost:3000
```

Select option **2) Include (pair) a device**, then triple-press the tamper
button on the sensor.  The script prints a node summary and value dump on
success.

### After pairing

The sensor is **battery-powered and sleeps most of the time**.  By default it
wakes and reports every 15 minutes (configurable via Z-Wave parameters).  Press
the button once to force an immediate measurement.

---

## Step 5 — Verify metrics

```bash
curl http://localhost:9100/metrics | grep zwave
```

Expected output:
```
zwave_temperature_celsius{endpoint="0",node_id="2",node_name="aerQ"} 22.5
zwave_humidity_percent{endpoint="0",node_id="2",node_name="aerQ"} 48.2
zwave_dew_point_celsius{endpoint="0",node_id="2",node_name="aerQ"} 10.8
zwave_node_alive{node_id="2",node_name="aerQ"} 1
zwave_node_battery_level{node_id="2",node_name="aerQ"} 100
```

> **Note:** Values will only appear after the sensor sends its first report.
> Press the tamper button once to force an immediate reading.

---

## Step 6 — Move to remote site

### Export the pairing state

```bash
docker run --rm \
  -v zwave-exporter_zwave-config:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/zwave-config.tar.gz -C /data .
```

Copy `zwave-config.tar.gz` and the entire project directory to the remote host.

### Restore on remote host

```bash
# On the remote host, in the project directory:
docker compose up --no-start   # creates volumes without starting
docker run --rm \
  -v zwave-exporter_zwave-config:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/zwave-config.tar.gz -C /data

docker compose up -d
```

The sensor will be recognized automatically — no re-pairing required.

---

## Prometheus configuration

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: "zwave"
    static_configs:
      - targets: ["<remote-host-ip>:9100"]
    scrape_interval: 30s
```

---

## Metrics reference

| Metric | Labels | Description |
|--------|--------|-------------|
| `zwave_temperature_celsius` | node_id, node_name, endpoint | Temperature (always in °C) |
| `zwave_humidity_percent` | node_id, node_name, endpoint | Relative humidity (%) |
| `zwave_dew_point_celsius` | node_id, node_name, endpoint | Dew point (°C) |
| `zwave_node_alive` | node_id, node_name | 1=alive/awake/asleep, 0=dead |
| `zwave_node_battery_level` | node_id, node_name | Battery % |
| `zwave_node_info` | node_id | Static info (manufacturer, firmware, etc.) |

---

## Troubleshooting

**zwave-js-ui won't start / can't open serial port**
```bash
# Check the device path
ls -la /dev/serial/by-id/
# Make sure your user is in the dialout group (Linux)
sudo usermod -aG dialout $USER
# On macOS the path will be something like /dev/cu.usbserial-...
```

**Sensor paired but no values appearing**
- Press the tamper button once to wake the sensor and force a report.
- In the zwave-js-ui Control Panel, click the node and check "Interview State".
  It should show "Complete".  If not, click "Re-interview".

**pair.py can't connect**
```bash
# Make sure port 3000 is exposed and zwave-js-ui is healthy
docker compose ps
curl http://localhost:8091/health
```

**Moving to a machine with a different USB path**
- Update `ZWAVE_DEVICE` in `.env` on the remote host.
- The node pairing data inside the volume is independent of the USB path.

**Factory reset the sensor (start over)**
- Hold the tamper button for 20 seconds.
- Run exclusion from the Web UI or pair.py option 3 first if possible.

---

## aërQ button reference

| Action | Result |
|--------|--------|
| Press 1× | Wake up / force measurement |
| Press 3× within 1s | Enter inclusion or exclusion mode |
| Hold 20s | Factory reset (no controller needed) |
