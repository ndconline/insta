# insta360-mic-pro-ctl

Unofficial cross-platform (Windows / macOS / Linux) tool to control the
[Insta360 Mic Pro](https://www.insta360.com/product/insta360-mic-pro) over
Bluetooth LE from a computer — mic mode, mic combination, noise reduction,
etc. — without the Android app.

**Status: protocol reverse-engineering in progress.** Insta360 does not
publish a spec for the Mic Pro's BLE control channel, so this repo does not
ship working "set noise reduction" commands out of the box. What it *does*
ship is a working toolkit to:

1. Find and connect to the mic and enumerate its real GATT services/characteristics.
2. Capture and decode what the official Android app sends when you change a
   setting, so you can map the real command bytes.
3. Send those commands from your computer once mapped, and save them here as
   they're discovered.

If you already own the mic, you're the fastest path to finishing this — steps
below take about 20 minutes.

## Why no ready-made commands?

There's no public SDK or protocol doc for the Mic Pro's BLE service (unlike
Insta360's cameras, which have a documented WiFi/protobuf API). The
options-setting screens only work when the app talks to the mic directly, so
the byte sequences have to be captured from a live app session — I don't have
the hardware to do that myself. Everything below is built so *you* can do it
in one sitting with your own phone and mic.

## Repo layout

```
src/insta360micpro/
  ble_explorer.py   # scan/connect/discover GATT structure, subscribe to notifications, send raw test bytes
  protocol.py        # InstaMicPro control class — fill in opcodes as you decode them
  cli.py              # command-line entry point wrapping the above
tools/
  snoop_parser.py    # parses an Android Bluetooth HCI snoop log and prints ATT reads/writes/notifications
docs/
  REVERSE_ENGINEERING.md   # step-by-step capture workflow
  PROTOCOL.md               # running notes / discovered opcode table (fill in as you go)
```

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate       # .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 1. Find the mic and dump its full GATT table
python -m insta360micpro.cli scan
python -m insta360micpro.cli discover --name "Insta360"

# 2. Watch live notifications while you press buttons on the mic itself
python -m insta360micpro.cli listen --address <MAC_OR_UUID>
```

Then follow `docs/REVERSE_ENGINEERING.md` to capture the app's traffic and
fill real opcodes into `protocol.py`.

## Contributing discovered opcodes

If you map a command, please open a PR adding it to `protocol.py` and a row
in `docs/PROTOCOL.md` with: setting name, characteristic UUID, request bytes,
response/notification bytes, and firmware version tested. This is the only
way this project becomes actually useful for everyone with the mic.

## Disclaimer

Unofficial, reverse-engineered, no affiliation with Insta360. Use at your own
risk — sending arbitrary bytes to a BLE characteristic is generally safe
(worst case is a no-op or a disconnect) but there's no guarantee against
firmware misbehavior. Don't send raw commands during a firmware update.

## License

MIT — see `LICENSE`.
