"""
Generic BLE exploration helpers built on bleak (cross-platform: Windows,
macOS, Linux). None of this is Insta360-specific — it's the toolkit you use
to *find out* what the Mic Pro's GATT layout looks like before protocol.py
can do anything useful.

Bleak docs: https://bleak.readthedocs.io/
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice


@dataclass
class DiscoveredCharacteristic:
    uuid: str
    handle: int
    properties: list[str]
    descriptors: list[str] = field(default_factory=list)


async def scan(timeout: float = 8.0, name_filter: str | None = None) -> list[BLEDevice]:
    """Scan for nearby BLE devices. Insta360 gear typically advertises with
    a name containing 'Insta360' but confirm with your own scan — some units
    only reveal a friendly name after the first connection."""
    print(f"Scanning for {timeout}s ...")
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    results: list[BLEDevice] = []
    for device, adv in devices.values():
        label = device.name or adv.local_name or "(unnamed)"
        if name_filter and name_filter.lower() not in label.lower():
            continue
        print(f"  {device.address}  rssi={adv.rssi:>5}  {label}")
        results.append(device)
    if not results:
        print("  (nothing found — make sure the mic is powered on and in "
              "pairing/discoverable mode, and that it isn't already "
              "connected to your phone)")
    return results


async def discover_gatt(address: str, timeout: float = 15.0) -> None:
    """Connect to a device and print its full service/characteristic/
    descriptor tree, including which properties (read/write/notify/etc.)
    each characteristic supports. This is the map you need before you can
    guess which characteristic is 'set mic mode' vs 'battery level' etc."""
    async with BleakClient(address, timeout=timeout) as client:
        print(f"Connected: {client.is_connected}")
        for service in client.services:
            print(f"\n[Service] {service.uuid}  ({service.description})")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  [Char] {char.uuid}  handle={char.handle}  props=[{props}]")
                for desc in char.descriptors:
                    print(f"    [Desc] {desc.uuid}  handle={desc.handle}")
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"    current value: {value.hex()}")
                    except Exception as exc:  # noqa: BLE001 - diagnostic tool
                        print(f"    (read failed: {exc})")


async def listen(address: str, duration: float = 60.0) -> None:
    """Subscribe to every notifiable/indicatable characteristic and print
    whatever comes through. Run this, then physically press buttons on the
    mic (mode button, mute button, etc.) to see what it reports — useful
    even without the phone app, since some state changes are pushed
    unprompted."""
    async with BleakClient(address) as client:
        notifiable = [
            char
            for service in client.services
            for char in service.characteristics
            if "notify" in char.properties or "indicate" in char.properties
        ]
        if not notifiable:
            print("No notifiable characteristics found.")
            return

        def make_handler(uuid: str):
            def handler(_, data: bytearray):
                print(f"[notify {uuid}] {data.hex()}")
            return handler

        for char in notifiable:
            await client.start_notify(char.uuid, make_handler(char.uuid))
            print(f"Subscribed: {char.uuid}")

        print(f"Listening for {duration}s — press buttons on the mic now ...")
        await asyncio.sleep(duration)

        for char in notifiable:
            await client.stop_notify(char.uuid)


async def write_raw(address: str, char_uuid: str, hex_bytes: str, response: bool = True) -> None:
    """Send a raw hex payload to a specific characteristic. This is how
    you'll test a hypothesis once you've decoded a command from a captured
    snoop log (see tools/snoop_parser.py and docs/REVERSE_ENGINEERING.md)."""
    payload = bytes.fromhex(hex_bytes.replace(" ", ""))
    async with BleakClient(address) as client:
        await client.write_gatt_char(char_uuid, payload, response=response)
        print(f"Wrote {payload.hex()} to {char_uuid} (response={response})")
