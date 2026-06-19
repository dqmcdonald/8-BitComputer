"""Upload a microcode ROM image to an AT28C256 EEPROM via the Arduino uploader.

The ROM images are produced by Simulator/microcode.py (rom1.bin / rom2.bin),
each a 1024-byte image addressed as [flags(9:8) | instr(7:3) | t_state(2:0)].
There are two ROMs, so run this once per ROM file (and per EEPROM).

For each byte the Arduino expects three bytes -- low address, high address,
data -- and replies with 0x55 once the write completes.

Example:
    python microcode_upload.py rom1.bin --port /dev/tty.usbmodem14101
"""

import argparse
import sys
import time

import serial

ACK = b"\x55"


def upload(rom_path: str, port: str, baud: int) -> None:
    with open(rom_path, "rb") as f:
        data = f.read()

    print(f"Uploading {len(data)} bytes from {rom_path} to {port} @ {baud} baud")

    with serial.Serial(port, baud, timeout=2) as ser:
        # Opening the port resets the Arduino; wait for the bootloader and
        # discard any boot noise so the byte stream stays in sync.
        time.sleep(2)
        ser.reset_input_buffer()

        for addr, byte in enumerate(data):
            ser.write(bytes([addr & 0xFF, (addr >> 8) & 0xFF, byte]))
            resp = ser.read()
            if resp != ACK:
                raise RuntimeError(
                    f"Upload failed at address {addr:#06x}: expected {ACK!r}, "
                    f"got {resp!r}"
                )
            if addr % 32 == 0:
                print(".", end="", flush=True)

    print("\nDone")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", help="ROM image to upload (e.g. rom1.bin)")
    parser.add_argument(
        "--port",
        default="/dev/tty.usbmodem14101",
        help="Serial port of the Arduino (default: %(default)s)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=9600,
        help="Baud rate (default: %(default)s)",
    )
    args = parser.parse_args()

    try:
        upload(args.rom, args.port, args.baud)
    except (OSError, serial.SerialException, RuntimeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
