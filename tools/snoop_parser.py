#!/usr/bin/env python3
"""
Parse an Android Bluetooth HCI snoop log (btsnoop_hci.log) and print every
ATT Write / Write Command / Read Response / Handle Value Notification —
i.e. exactly the traffic you need to decode the Insta360 app's control
protocol for the Mic Pro.

How to get the log (Android):
    1. Settings > System > Developer options > enable "Bluetooth HCI
       snoop log" (on some phones it's under a "Bug report" or
       "Wireless debugging" section instead).
    2. Turn Bluetooth off and back on (some OEMs need a reboot for the
       toggle to take effect).
    3. Open the Insta360 app, connect to the Mic Pro, and change ONE
       setting at a time (e.g. just flip noise reduction from Low to
       High), waiting a couple seconds between each change so it's easy
       to line up cause and effect afterward.
    4. Pull the log:
       adb bugreport report.zip
       (the file is inside as FS/data/misc/bluetooth/logs/btsnoop_hci.log,
       or sometimes /sdcard/btsnoop_hci.log directly — unzip and grab it)
    5. Run this script against it.

Usage:
    python snoop_parser.py btsnoop_hci.log
    python snoop_parser.py btsnoop_hci.log --address AA:BB:CC:DD:EE:FF
"""

from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass

BTSNOOP_HDR_MAGIC = b"btsnoop\x00"

# HCI packet type markers used in the pseudo-header bluez/Android writes
HCI_CMD = 0x01
HCI_ACL = 0x02
HCI_SCO = 0x03
HCI_EVT = 0x04

ATT_OPCODES = {
    0x0B: "Read Response",
    0x12: "Write Request",
    0x13: "Write Response",
    0x1B: "Handle Value Notification",
    0x1D: "Handle Value Indication",
    0x52: "Write Command",
}


@dataclass
class AttRecord:
    index: int
    direction: str
    opcode_name: str
    handle: int | None
    payload: bytes


def _iter_btsnoop_records(path: str):
    with open(path, "rb") as f:
        magic = f.read(8)
        if magic != BTSNOOP_HDR_MAGIC:
            raise ValueError("Not a btsnoop file (bad magic) — did you point this at the right log?")
        f.read(4)  # datalink type

        index = 0
        while True:
            hdr = f.read(24)
            if len(hdr) < 24:
                break
            orig_len, incl_len, flags, drops, ts = struct.unpack(">IIIIq", hdr)
            data = f.read(incl_len)
            if len(data) < incl_len:
                break
            index += 1
            # flags bit 0: 0 = sent (host->controller), 1 = received
            direction = "TX" if (flags & 0x01) == 0 else "RX"
            yield index, direction, data


def _extract_att_from_acl(data: bytes):
    """Best-effort ACL -> L2CAP -> ATT unwrap. HCI ACL header is 4 bytes,
    then a 4-byte L2CAP header (length, cid). ATT's CID is 0x0004."""
    if len(data) < 9:
        return None
    # data[0] is the HCI packet indicator only present in some capture
    # variants; btsnoop ACL records from Android already start at the HCI
    # ACL header, so no extra offset here.
    l2cap_len, cid = struct.unpack_from("<HH", data, 4)
    if cid != 0x0004:  # not ATT
        return None
    att = data[8:8 + l2cap_len]
    if not att:
        return None
    return att


def parse(path: str, address_filter: str | None = None) -> list[AttRecord]:
    records: list[AttRecord] = []
    for index, direction, data in _iter_btsnoop_records(path):
        if not data:
            continue
        pkt_type = data[0]
        body = data[1:]
        if pkt_type != HCI_ACL:
            continue
        att = _extract_att_from_acl(body)
        if not att:
            continue
        opcode = att[0]
        name = ATT_OPCODES.get(opcode)
        if not name:
            continue
        handle = None
        payload = b""
        if opcode in (0x12, 0x52, 0x1B, 0x1D) and len(att) >= 3:
            handle = struct.unpack_from("<H", att, 1)[0]
            payload = att[3:]
        elif opcode == 0x0B:
            payload = att[1:]
        records.append(AttRecord(index, direction, name, handle, payload))

    # Note: this parser doesn't currently filter by BLE peer address
    # because that requires correlating ACL connection handles back to the
    # LE Connection Complete event. For a first pass, if you only had ONE
    # BLE device connected during the capture window, every record here is
    # already from your mic. If you had others connected too, trim the
    # capture window (steps 3-4 above) rather than filtering here.
    if address_filter:
        print(f"(note: --address filtering not implemented; capture window "
              f"should already isolate {address_filter} traffic — see script docstring)")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("log", help="path to btsnoop_hci.log")
    parser.add_argument("--address", default=None, help="(informational only, see notes)")
    args = parser.parse_args()

    records = parse(args.log, args.address)
    if not records:
        print("No ATT read/write/notify records found. Common causes: "
              "wrong file, capture didn't include the setting change, or "
              "device uses classic Bluetooth (RFCOMM/SPP) instead of BLE "
              "for this operation — check for HCI_ACL frames on a classic "
              "connection handle too, that's outside this script's scope.")
        return

    for r in records:
        h = f"handle=0x{r.handle:04x}" if r.handle is not None else ""
        print(f"#{r.index:>6} [{r.direction}] {r.opcode_name:<28} {h:<14} {r.payload.hex()}")


if __name__ == "__main__":
    main()
