# Discovered protocol notes

Fill this in as you decode commands (see REVERSE_ENGINEERING.md). Keep one
row per confirmed setting.

## GATT structure

| Service UUID | Description | Notes |
|---|---|---|
| `00001800-...` | Generic Access | standard |
| `0000180a-...` | Device Information | standard |
| `0000180f-...` | Battery Service | standard, try this first via `cli.py battery` |
| _(TODO)_ | Mic Pro control service | fill in from `discover` output |

## Confirmed commands

| Setting | Characteristic UUID | Write bytes (hex) | Response type | Notes | FW version |
|---|---|---|---|---|---|
| _(none yet)_ | | | | | |

Example row once filled in:

| Noise reduction: High | `0000ffe1-0000-1000-8000-00805f9b34fb` | `a5 01 02 a8` | Write Command | byte 3 = mode (00 off / 01 low / 02 high), byte 4 = checksum (sum of preceding bytes & 0xFF) | 1.2.3 |

## Open questions

- Is there a fixed frame header/checksum, or are these raw enum values?
- Do TX (transmitter) and RX (receiver) units expose the same control
  service, or does the receiver proxy commands to paired transmitters?
- Does the mic require the notify characteristic to be subscribed before
  it accepts writes?
