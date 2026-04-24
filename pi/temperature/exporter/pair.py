#!/usr/bin/env python3
"""
pair.py — Interactive Z-Wave inclusion/exclusion helper.

Run this against a live zwave-js-server to:
  • List currently known nodes
  • Start inclusion (add) mode so you can pair the Aeotec aërQ
  • Start exclusion (remove) mode to factory-reset/unpair a node
  • Check node values

Usage:
    python pair.py [--url ws://localhost:3000]

The script drives inclusion for 60 seconds then stops.  During that window,
triple-press the tamper button on the aërQ sensor (3× within 1 second).
"""

import argparse
import asyncio
import json
import logging
import sys

import aiohttp
from zwave_js_server.client import Client
from zwave_js_server.model.controller import InclusionStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pair")


def _node_summary(node) -> str:
    dc = node.device_config
    mfr = dc.manufacturer if dc else "?"
    prod = dc.label if dc else "?"
    return (
        f"  Node {node.node_id:3d}  name={node.name or '(none)':20s}  "
        f"status={node.status.name:8s}  {mfr} / {prod}"
    )


async def list_nodes(client: Client) -> None:
    print("\n── Known nodes ──────────────────────────────────────────────────────")
    nodes = client.driver.controller.nodes
    if not nodes:
        print("  (no nodes)")
    for node in sorted(nodes.values(), key=lambda n: n.node_id):
        print(_node_summary(node))
    print()


async def dump_values(client: Client, node_id: int) -> None:
    node = client.driver.controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return
    print(f"\n── Values for node {node_id} ────────────────────────────────────────")
    for vid, val in sorted(node.values.items()):
        print(
            f"  cc={val.command_class_id:3d}  prop={str(val.property):30s}  "
            f"propKey={str(val.property_key):5s}  value={val.value}  unit={getattr(val.metadata, 'unit', '')}"
        )
    print()


async def do_inclusion(client: Client, timeout: int = 60) -> None:
    controller = client.driver.controller

    added_event = asyncio.Event()
    added_node = {}

    def on_node_added(event: dict):
        node = event["node"]
        added_node["node"] = node
        log.info("✓ Node added: id=%d  name=%s", node.node_id, node.name or "(unnamed)")
        added_event.set()

    def on_inclusion_failed(event: dict):
        log.error("✗ Inclusion failed: %s", event)

    controller.on("node added", on_node_added)
    controller.on("inclusion failed", on_inclusion_failed)

    log.info("Starting inclusion mode for %ds …", timeout)
    log.info("→ Now triple-press the tamper button on the aërQ sensor (3× within 1 second).")

    # InclusionStrategy.DEFAULT lets the controller auto-select S2/S0 security
    result = await controller.async_begin_inclusion(InclusionStrategy.DEFAULT)
    if not result:
        log.error("Controller refused to start inclusion — is it already in a mode?")
        return

    try:
        await asyncio.wait_for(added_event.wait(), timeout=timeout)
        node = added_node.get("node")
        if node:
            print(f"\n✓ Successfully paired: {_node_summary(node)}\n")
            # Give it a moment to finish interview
            await asyncio.sleep(3)
            await dump_values(client, node.node_id)
    except asyncio.TimeoutError:
        log.warning("Inclusion timed out — no device detected in %ds", timeout)
    finally:
        await controller.async_stop_inclusion()
        log.info("Inclusion mode stopped.")


async def do_inclusion_insecure(client: Client, timeout: int = 60) -> None:
    """Pair a device with no S2/S0 security (InclusionStrategy.INSECURE).

    Use this when DEFAULT inclusion always fails S2 bootstrapping.  Fine for
    sensors where encryption isn't required.
    """
    controller = client.driver.controller

    added_event = asyncio.Event()
    added_node = {}

    def on_node_added(event: dict):
        node = event["node"]
        added_node["node"] = node
        log.info("✓ Node added (insecure): id=%d  name=%s", node.node_id, node.name or "(unnamed)")
        added_event.set()

    def on_inclusion_failed(event: dict):
        log.error("✗ Inclusion failed: %s", event)

    controller.on("node added", on_node_added)
    controller.on("inclusion failed", on_inclusion_failed)

    log.info("Starting INSECURE inclusion for %ds …", timeout)
    log.info("→ Triple-press the tamper button on the aërQ sensor (3× within 1 second).")

    result = await controller.async_begin_inclusion(InclusionStrategy.INSECURE)
    if not result:
        log.error("Controller refused to start inclusion — is it already in a mode?")
        return

    try:
        await asyncio.wait_for(added_event.wait(), timeout=timeout)
        node = added_node.get("node")
        if node:
            print(f"\n✓ Successfully paired (insecure): {_node_summary(node)}\n")
            log.info("Waiting 5s for interview to start…")
            await asyncio.sleep(5)
            await dump_values(client, node.node_id)
    except asyncio.TimeoutError:
        log.warning("Inclusion timed out — no device detected in %ds", timeout)
    finally:
        await controller.async_stop_inclusion()
        log.info("Inclusion mode stopped.")


async def do_exclusion(client: Client, timeout: int = 30) -> None:
    controller = client.driver.controller

    removed_event = asyncio.Event()

    def on_node_removed(event: dict):
        log.info("✓ Node removed: id=%d", event.get("node", {}).node_id if event.get("node") else "?")
        removed_event.set()

    controller.on("node removed", on_node_removed)

    log.info("Starting exclusion mode for %ds …", timeout)
    log.info("→ Triple-press the tamper button on the device you want to remove.")

    result = await controller.async_begin_exclusion()
    if not result:
        log.error("Controller refused to start exclusion.")
        return

    try:
        await asyncio.wait_for(removed_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        log.warning("Exclusion timed out — no device detected in %ds", timeout)
    finally:
        await controller.async_stop_exclusion()
        log.info("Exclusion mode stopped.")


async def remove_failed(client: Client, node_id: int) -> None:
    controller = client.driver.controller
    node = controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return
    log.info("Force-removing failed node %d from controller…", node_id)
    await controller.async_remove_failed_node(node)
    log.info("Node %d removed. Now factory-reset the device and re-pair.", node_id)


async def set_wakeup_interval(client: Client, node_id: int, interval_seconds: int) -> None:
    """Set the wakeup interval for a battery node.

    The command is queued immediately and will be delivered the next time
    the node wakes up.  Triple-press the tamper button after running this
    to trigger a wakeup and apply the change.
    """
    node = client.driver.controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return

    # Find the wakeUpInterval value (Wake Up CC = 0x84 = 132)
    wakeup_value = None
    for val in node.values.values():
        if val.command_class == 0x84 and val.property_ == "wakeUpInterval":
            wakeup_value = val
            break

    if wakeup_value is None:
        log.error("Could not find wakeUpInterval value for node %d — is Wake Up CC supported?", node_id)
        return

    log.info("Queuing wakeup interval = %ds for node %d (currently %s)",
             interval_seconds, node_id, wakeup_value.value)
    await node.async_set_value(wakeup_value.value_id, interval_seconds)
    log.info("Queued. Now triple-press the tamper button to wake the node and apply the change.")


async def re_interview(client: Client, node_id: int) -> None:
    node = client.driver.controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return
    log.info("Triggering re-interview for node %d — wake the device now!", node_id)
    await node.async_interview()
    log.info("Re-interview complete for node %d", node_id)


async def watch_and_refresh(client: Client, node_id: int) -> None:
    """Listen for wakeup events and immediately queue a full value refresh.

    Battery devices have a short wakeup window. By triggering async_refresh_values()
    the instant the wakeup notification arrives we get commands queued before the
    device goes back to sleep.  Press Ctrl-C to stop watching.
    """
    node = client.driver.controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return

    wakeup_count = 0

    def on_wakeup(event: dict) -> None:
        nonlocal wakeup_count
        wakeup_count += 1
        log.info("Node %d woke up (#%d) — queuing value refresh immediately", node_id, wakeup_count)
        asyncio.create_task(node.async_refresh_values())

    node.on("wake up", on_wakeup)
    log.info("Watching node %d for wakeups — press Ctrl-C to stop. Wake the device now.", node_id)
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        log.info("Stopped watching node %d (%d wakeup(s) seen)", node_id, wakeup_count)


async def interview_on_wakeup(client: Client, node_id: int) -> None:
    """Wait for the node's next wakeup event and immediately trigger a full interview.

    Use this when async_interview() fails because the node is asleep.  The interview
    command is fired the instant the wakeup notification arrives, maximising the
    chance it lands inside the wakeup window.  Exits after the first wakeup.
    """
    node = client.driver.controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return

    done = asyncio.Event()

    def on_wakeup(event: dict) -> None:
        log.info("Node %d woke up — triggering interview now", node_id)
        asyncio.create_task(node.async_interview())
        done.set()

    node.on("wake up", on_wakeup)
    log.info("Waiting for node %d to wake up — wake the device now (triple-press tamper).", node_id)
    try:
        await done.wait()
        log.info("Interview triggered — waiting 30s for it to complete…")
        await asyncio.sleep(30)
        await dump_values(client, node_id)
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("Cancelled — interview may still be in progress.")
    finally:
        node.off("wake up", on_wakeup)


async def set_config_param(client: Client, node_id: int, param: int, value: int) -> None:
    """Set a Configuration CC parameter on a node.

    The command is queued and delivered on the next wakeup for sleeping nodes.
    Triple-press the tamper button after running this to apply immediately.
    """
    node = client.driver.controller.nodes.get(node_id)
    if node is None:
        print(f"Node {node_id} not found")
        return

    # Find the config value — match on CC 112 (Configuration) and property == param number
    config_value = None
    for val in node.values.values():
        if val.command_class == 112 and val.property_ == param and val.property_key is None:
            config_value = val
            break

    if config_value is None:
        log.error("Config parameter #%d not found for node %d", param, node_id)
        log.info("Available config params: %s", sorted(
            v.property_ for v in node.values.values() if v.command_class == 112
        ))
        return

    label = config_value.metadata.label if config_value.metadata else f"param #{param}"
    log.info("Queuing node %d config param #%d (%s) = %d (was %s)",
             node_id, param, label, value, config_value.value)
    await node.async_set_value(config_value.value_id, value)
    log.info("Queued. Triple-press tamper to wake the node and apply.")


async def heal_network(client: Client) -> None:
    log.info("Healing Z-Wave network (this may take a few minutes)…")
    await client.driver.controller.async_heal_network()
    log.info("Heal complete.")


async def main_menu(url: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with Client(url, session) as client:
            await client.connect()
            log.info("Connected — zwave-js-server %s", client.version)

            driver_ready = asyncio.Event()
            listen_task = asyncio.create_task(client.listen(driver_ready))
            await asyncio.wait_for(driver_ready.wait(), timeout=10)
            log.info("Driver ready")

            while True:
                print("""
┌─────────────────────────────────────────┐
│  Z-Wave Pairing Helper                  │
├─────────────────────────────────────────┤
│  1) List nodes                          │
│  2) Include (pair) a device             │
│  2i) Include insecure (skip S2/S0)     │
│  3) Exclude (unpair / factory-reset)    │
│  4) Dump values for a node              │
│  5) Heal network                        │
│  6) Re-interview a node                 │
│  7) Force-remove a failed node          │
│  8) Watch node & refresh on wakeup      │
│  9) Interview node on next wakeup       │
│  w) Set wakeup interval (seconds)      │
│  c) Set config parameter               │
│  q) Quit                                │
└─────────────────────────────────────────┘""")
                choice = input("Choice: ").strip().lower()

                if choice == "1":
                    await list_nodes(client)
                elif choice == "2i":
                    await do_inclusion_insecure(client)
                elif choice == "2":
                    await do_inclusion(client)
                elif choice == "3":
                    await do_exclusion(client)
                elif choice == "4":
                    nid = input("Node ID: ").strip()
                    if nid.isdigit():
                        await dump_values(client, int(nid))
                elif choice == "5":
                    await heal_network(client)
                elif choice == "6":
                    nid = input("Node ID: ").strip()
                    if nid.isdigit():
                        await re_interview(client, int(nid))
                elif choice == "7":
                    nid = input("Node ID: ").strip()
                    if nid.isdigit():
                        await remove_failed(client, int(nid))
                elif choice == "8":
                    nid = input("Node ID: ").strip()
                    if nid.isdigit():
                        await watch_and_refresh(client, int(nid))
                elif choice == "9":
                    nid = input("Node ID: ").strip()
                    if nid.isdigit():
                        await interview_on_wakeup(client, int(nid))
                elif choice == "w":
                    nid = input("Node ID: ").strip()
                    secs = input("Interval (seconds) [1800]: ").strip() or "1800"
                    if nid.isdigit() and secs.isdigit():
                        await set_wakeup_interval(client, int(nid), int(secs))
                elif choice == "c":
                    nid = input("Node ID: ").strip()
                    param = input("Parameter #: ").strip()
                    val = input("Value: ").strip()
                    if nid.isdigit() and param.isdigit() and val.lstrip("-").isdigit():
                        await set_config_param(client, int(nid), int(param), int(val))
                elif choice in ("q", "quit", "exit"):
                    listen_task.cancel()
                    break
                else:
                    print("Unknown choice.")


def main():
    parser = argparse.ArgumentParser(description="Z-Wave pairing helper")
    parser.add_argument(
        "--url",
        default="ws://localhost:3000",
        help="zwave-js-server WebSocket URL (default: ws://localhost:3000)",
    )
    args = parser.parse_args()
    asyncio.run(main_menu(args.url))


if __name__ == "__main__":
    main()
