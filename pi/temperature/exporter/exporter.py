#!/usr/bin/env python3
"""
Z-Wave Prometheus Exporter
Connects to zwave-js-server via WebSocket and exports temperature/humidity metrics.
"""

import asyncio
import logging
import os
import signal

import aiohttp
from prometheus_client import Gauge, Info, start_http_server
from zwave_js_server.client import Client
from zwave_js_server.model.node import Node
from zwave_js_server.model.value import Value

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("zwave-exporter")

# ── Prometheus metrics ──────────────────────────────────────────────────────────
TEMPERATURE = Gauge(
    "zwave_temperature_celsius",
    "Temperature reading from Z-Wave sensor",
    ["node_id", "node_name", "endpoint"],
)
HUMIDITY = Gauge(
    "zwave_humidity_percent",
    "Relative humidity reading from Z-Wave sensor",
    ["node_id", "node_name", "endpoint"],
)
DEW_POINT = Gauge(
    "zwave_dew_point_celsius",
    "Dew point reading from Z-Wave sensor",
    ["node_id", "node_name", "endpoint"],
)
NODE_ALIVE = Gauge(
    "zwave_node_alive",
    "1 if the Z-Wave node is alive/awake, 0 otherwise",
    ["node_id", "node_name"],
)
NODE_BATTERY = Gauge(
    "zwave_node_battery_level",
    "Battery level of Z-Wave node (0-100)",
    ["node_id", "node_name"],
)
NODE_INFO = Info(
    "zwave_node",
    "Static metadata about a Z-Wave node",
    ["node_id"],
)

# Z-Wave Command Class IDs
CC_SENSOR_MULTILEVEL = 49
CC_BATTERY = 128

# Multilevel Sensor CC property names (value.property_ is the string sensor type name)
SENSOR_TYPE_TEMPERATURE = "Air temperature"
SENSOR_TYPE_HUMIDITY = "Humidity"
SENSOR_TYPE_DEW_POINT = "Dew point"


def _node_label(node: Node) -> dict:
    return {
        "node_id": str(node.node_id),
        "node_name": node.name or f"node_{node.node_id}",
    }


def _process_value(node: Node, value: Value) -> None:
    if value.value is None:
        return

    node_id = str(node.node_id)
    node_name = node.name or f"node_{node.node_id}"
    endpoint = str(value.endpoint)

    if value.command_class == CC_SENSOR_MULTILEVEL:
        sensor_type = value.property_  # numeric sensor type code (1=temp, 5=humidity, 11=dew point)
        log.debug("node %s  multilevel sensor type=%s key=%s value=%s unit=%s",
                  node_id, sensor_type, value.property_key, value.value,
                  getattr(value.metadata, "unit", None))

        if sensor_type == SENSOR_TYPE_TEMPERATURE:
            val = float(value.value)
            unit = (value.metadata.unit or "").strip()
            if unit == "°F":
                val = (val - 32) * 5 / 9
            TEMPERATURE.labels(node_id=node_id, node_name=node_name, endpoint=endpoint).set(val)
            log.info("node %s  temperature=%.2f°C", node_id, val)

        elif sensor_type == SENSOR_TYPE_HUMIDITY:
            HUMIDITY.labels(node_id=node_id, node_name=node_name, endpoint=endpoint).set(float(value.value))
            log.info("node %s  humidity=%.1f%%", node_id, float(value.value))

        elif sensor_type == SENSOR_TYPE_DEW_POINT:
            val = float(value.value)
            unit = (value.metadata.unit or "").strip()
            if unit == "°F":
                val = (val - 32) * 5 / 9
            DEW_POINT.labels(node_id=node_id, node_name=node_name, endpoint=endpoint).set(val)
            log.info("node %s  dew_point=%.2f°C", node_id, val)

        else:
            log.debug("node %s  unhandled multilevel sensor type=%s", node_id, sensor_type)

    elif value.command_class == CC_BATTERY:
        if value.property_ == "level":
            lbl = _node_label(node)
            NODE_BATTERY.labels(**lbl).set(float(value.value))
            log.info("node %s  battery=%s%%", node_id, value.value)


def _update_node_alive(node: Node) -> None:
    lbl = _node_label(node)
    # NodeStatus: Unknown=0, Asleep=1, Awake=2, Dead=3, Alive=4
    alive = 1 if node.status.value in (1, 2, 4) else 0
    NODE_ALIVE.labels(**lbl).set(alive)


def _publish_node_info(node: Node) -> None:
    lbl = _node_label(node)
    NODE_INFO.labels(node_id=lbl["node_id"]).info({
        "name": node.name or "",
        "manufacturer": (node.device_config.manufacturer or "") if node.device_config else "",
        "product": (node.device_config.label or "") if node.device_config else "",
        "firmware_version": node.firmware_version or "",
    })


def _seed_node(node: Node) -> None:
    for value in node.values.values():
        _process_value(node, value)
    _update_node_alive(node)
    _publish_node_info(node)


def _attach_node_listeners(node: Node) -> None:
    def on_value_updated(event: dict) -> None:
        _process_value(event["node"], event["value"])

    def on_status_changed(event: dict) -> None:
        _update_node_alive(event["node"])

    node.on("value updated", on_value_updated)
    node.on("alive", on_status_changed)
    node.on("dead", on_status_changed)
    node.on("sleep", on_status_changed)
    node.on("wake up", on_status_changed)


async def run(zwave_ws_url: str, metrics_port: int) -> None:
    log.info("Starting Prometheus HTTP server on :%d", metrics_port)
    start_http_server(metrics_port)

    reconnect_delay = 5

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                log.info("Connecting to zwave-js-server at %s", zwave_ws_url)
                async with Client(zwave_ws_url, session) as client:
                    await client.connect()
                    log.info("Connected — %s", client.version)
                    reconnect_delay = 5

                    driver_ready = asyncio.Event()
                    listen_task = asyncio.create_task(client.listen(driver_ready))
                    await asyncio.wait_for(driver_ready.wait(), timeout=10)

                    driver = client.driver
                    controller = driver.controller

                    log.info("Driver ready — %d node(s) known", len(controller.nodes))

                    # Seed existing nodes
                    for node in controller.nodes.values():
                        log.info("Seeding node %d (%s)", node.node_id, node.name or "unnamed")
                        _attach_node_listeners(node)
                        _seed_node(node)

                    # Handle nodes added after startup (e.g. during pairing)
                    def on_node_added(event: dict) -> None:
                        node: Node = event["node"]
                        log.info("Node added: %d", node.node_id)
                        _attach_node_listeners(node)
                        _seed_node(node)

                    controller.on("node added", on_node_added)

                    log.info("Listening for Z-Wave events…")
                    await listen_task

            except Exception as exc:
                log.error("Connection error: %s — reconnecting in %ds", exc, reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)


def main() -> None:
    zwave_ws = os.environ.get("ZWAVE_WS_URL", "ws://zwave-js-ui:3000")
    metrics_port = int(os.environ.get("METRICS_PORT", "9100"))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _shutdown(sig, frame):
        log.info("Caught signal %s — shutting down", sig)
        loop.stop()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(run(zwave_ws, metrics_port))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
