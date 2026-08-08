"""
InstaMicPro — high-level control class for the Insta360 Mic Pro.

IMPORTANT: The UUIDs and command bytes below are placeholders. Insta360
hasn't published this protocol, so every ``TODO`` here needs to be filled in
by capturing real traffic between the official Android app and your mic —
see docs/REVERSE_ENGINEERING.md for the exact steps, and
tools/snoop_parser.py to decode the capture.

Once you've confirmed a command works, replace the placeholder and it
becomes real. This class is intentionally structured so that's a one-line
change per setting, not a rewrite.
"""

from __future__ import annotations

from enum import Enum

from bleak import BleakClient

# TODO: replace with the real custom service/characteristic UUIDs from
# `python -m insta360micpro.cli discover`. Standard GATT services (Battery,
# Device Info) will have well-known short UUIDs; the mic-control service
# will almost certainly be a vendor-specific 128-bit UUID that only shows up
# once you're connected.
CONTROL_SERVICE_UUID = "0000XXXX-0000-1000-8000-00805f9b34fb"
CONTROL_WRITE_CHAR_UUID = "0000YYYY-0000-1000-8000-00805f9b34fb"
CONTROL_NOTIFY_CHAR_UUID = "0000ZZZZ-0000-1000-8000-00805f9b34fb"


class MicMode(Enum):
    """Which physical mic capsule(s) are active. Names match the product
    page's terminology; TODO confirm exact wire values from a capture."""
    OMNIDIRECTIONAL = "TODO"   # top single mic only
    DIRECTIONAL = "TODO"       # directional pickup, all 3 mics
    STEREO = "TODO"            # stereo internal recording, all 3 mics


class NoiseReductionMode(Enum):
    OFF = "TODO"
    LOW = "TODO"
    HIGH = "TODO"


class InstaMicPro:
    """Wraps a BleakClient connection to one Mic Pro receiver/transmitter
    and exposes settings as plain method calls.

    Usage (once opcodes below are filled in):

        async with InstaMicPro(address) as mic:
            await mic.set_mic_mode(MicMode.DIRECTIONAL)
            await mic.set_noise_reduction(NoiseReductionMode.HIGH)
    """

    def __init__(self, address: str):
        self.address = address
        self._client: BleakClient | None = None

    async def __aenter__(self) -> "InstaMicPro":
        self._client = BleakClient(self.address)
        await self._client.connect()
        return self

    async def __aexit__(self, *exc_info) -> None:
        if self._client:
            await self._client.disconnect()

    async def _write(self, payload: bytes, response: bool = True) -> None:
        assert self._client is not None, "use `async with InstaMicPro(...) as mic:`"
        await self._client.write_gatt_char(CONTROL_WRITE_CHAR_UUID, payload, response=response)

    # ------------------------------------------------------------------
    # Settings — each of these is a stub until the TODO opcode is filled.
    # Pattern to follow once you decode a command from the snoop capture:
    #   payload = bytes([0xA5, 0x01, mode.value, checksum])
    # Real Insta360 BLE traffic is often a small framed protocol (start
    # byte / command id / payload / checksum) similar to their WiFi
    # protobuf frames — but confirm this from your own capture rather than
    # assuming it.
    # ------------------------------------------------------------------

    async def set_mic_mode(self, mode: MicMode) -> None:
        raise NotImplementedError(
            "Opcode for set_mic_mode not yet reverse-engineered. "
            "See docs/REVERSE_ENGINEERING.md."
        )

    async def set_noise_reduction(self, mode: NoiseReductionMode) -> None:
        raise NotImplementedError(
            "Opcode for set_noise_reduction not yet reverse-engineered. "
            "See docs/REVERSE_ENGINEERING.md."
        )

    async def get_battery_level(self) -> int:
        """Standard Battery Service (0x180F) may already work unmodified —
        try this one first, it's often not vendor-custom."""
        assert self._client is not None
        value = await self._client.read_gatt_char("00002a19-0000-1000-8000-00805f9b34fb")
        return value[0]
