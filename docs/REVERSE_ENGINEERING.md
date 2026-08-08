# Reverse-engineering the Mic Pro's BLE protocol

Goal: figure out which bytes the Insta360 app writes to which
characteristic when you toggle a setting, so `protocol.py` can send them
directly from a computer.

## 1. Map the GATT structure first

```bash
python -m insta360micpro.cli scan --name Insta360
python -m insta360micpro.cli discover --address <ADDRESS_FROM_SCAN>
```

This prints every service/characteristic/descriptor UUID and which are
readable/writable/notifiable. Write these down — you'll be looking for a
vendor-specific (long, not "0000XXXX-...") service that isn't Battery
(0x180F) or Device Information (0x180A). That's almost certainly the
control channel.

## 2. Capture the app talking to the mic

1. On the Android phone: **Settings → System → Developer options → enable
   "Bluetooth HCI snoop log"**. (If you don't see Developer options, tap
   Build Number 7 times under About Phone first.)
2. Toggle Bluetooth off/on so the new logging setting takes effect.
3. Open the Insta360 app, connect to the Mic Pro.
4. Change **one setting at a time**, e.g.:
   - Noise reduction: Off → Low → High → Off
   - Mic mode: Omnidirectional → Directional → Stereo
   Pause a couple seconds between each change — it makes the log much
   easier to read afterward.
5. Pull the log off the phone:
   ```bash
   adb bugreport report.zip
   unzip report.zip -d report
   find report -name "btsnoop_hci.log"
   ```
   (Some OEMs write directly to `/sdcard/btsnoop_hci.log` — check there
   first if `adb bugreport` is slow or unavailable.)

## 3. Decode the capture

```bash
python tools/snoop_parser.py report/FS/data/misc/bluetooth/logs/btsnoop_hci.log
```

This prints every ATT Write Request / Write Command / Notification with
its handle and hex payload, in order. Because you changed settings one at
a time with pauses, you can usually eyeball which write corresponds to
which change — e.g. if you set noise reduction to Low then High then Off,
look for three writes to the same handle where one byte cycles through
what look like 3 small values.

Cross-reference the handle number against the `discover` output from step 1
to get back to a characteristic UUID.

## 4. Confirm your guess

```bash
python -m insta360micpro.cli write \
  --address <ADDRESS> \
  --char <CHARACTERISTIC_UUID_FROM_STEP_3> \
  --hex "<PAYLOAD_HEX>"
```

Watch the mic's display / listen for the physical setting to change. If it
does, you've got a confirmed command — update `protocol.py` and add a row
to `docs/PROTOCOL.md`.

If nothing happens, common culprits:
- **Wrong response mode.** Try both `write` and `write --no-response`
  (Write Request vs Write Command — the snoop log tells you which the app
  used, opcode `0x12` vs `0x52`).
- **Missing preamble/checksum.** Insta360's WiFi protocol (documented
  separately by other reverse-engineers) uses framed protobuf messages;
  their BLE frames may similarly need a fixed header or trailing checksum
  byte that's easy to miss if you only look at one example. Capture the
  same setting change twice and diff the payloads — the parts that stay
  constant across both captures are probably framing, not data.
- **CCCD not enabled.** Some devices only accept commands after a client
  has subscribed to the paired notify characteristic (even if you don't
  care about the notifications). Try calling `listen` on that
  characteristic in another terminal first, then `write`.

## 5. Save it

Add the working command to `docs/PROTOCOL.md` and wire it into the
matching method in `protocol.py`, replacing its `NotImplementedError`.
