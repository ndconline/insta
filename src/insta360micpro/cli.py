"""Command-line entry point.

Examples:
    python -m insta360micpro.cli scan
    python -m insta360micpro.cli scan --name Insta360
    python -m insta360micpro.cli discover --address AA:BB:CC:DD:EE:FF
    python -m insta360micpro.cli listen --address AA:BB:CC:DD:EE:FF --seconds 30
    python -m insta360micpro.cli write --address AA:BB:CC:DD:EE:FF \\
        --char 0000ffe1-0000-1000-8000-00805f9b34fb --hex "a5 01 02 a8"
    python -m insta360micpro.cli battery --address AA:BB:CC:DD:EE:FF
"""

from __future__ import annotations

import argparse
import asyncio

from . import ble_explorer
from .protocol import InstaMicPro


def main() -> None:
    parser = argparse.ArgumentParser(prog="insta360micpro")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="scan for nearby BLE devices")
    p_scan.add_argument("--seconds", type=float, default=8.0)
    p_scan.add_argument("--name", default=None, help="filter by substring in advertised name")

    p_disc = sub.add_parser("discover", help="connect and print full GATT table")
    p_disc.add_argument("--address", required=True, help="MAC address (or UUID on macOS)")

    p_listen = sub.add_parser("listen", help="subscribe to all notify characteristics")
    p_listen.add_argument("--address", required=True)
    p_listen.add_argument("--seconds", type=float, default=60.0)

    p_write = sub.add_parser("write", help="write raw hex bytes to a characteristic")
    p_write.add_argument("--address", required=True)
    p_write.add_argument("--char", required=True, help="characteristic UUID")
    p_write.add_argument("--hex", required=True, help="hex payload, e.g. 'a5 01 02 a8'")
    p_write.add_argument("--no-response", action="store_true")

    p_batt = sub.add_parser("battery", help="read standard battery level characteristic")
    p_batt.add_argument("--address", required=True)

    args = parser.parse_args()

    if args.command == "scan":
        asyncio.run(ble_explorer.scan(timeout=args.seconds, name_filter=args.name))
    elif args.command == "discover":
        asyncio.run(ble_explorer.discover_gatt(args.address))
    elif args.command == "listen":
        asyncio.run(ble_explorer.listen(args.address, duration=args.seconds))
    elif args.command == "write":
        asyncio.run(
            ble_explorer.write_raw(
                args.address, args.char, args.hex, response=not args.no_response
            )
        )
    elif args.command == "battery":
        async def _run():
            async with InstaMicPro(args.address) as mic:
                print(f"Battery: {await mic.get_battery_level()}%")
        asyncio.run(_run())


if __name__ == "__main__":
    main()
