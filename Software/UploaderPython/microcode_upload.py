"""Upload a microcode ROM image to an AT28C256 EEPROM via the Arduino uploader.

The ROM images are produced by Simulator/microcode.py (rom1.bin / rom2.bin),
each a 1024-byte image addressed as [flags(9:8) | instr(7:3) | t_state(2:0)].
There are two ROMs, so run this once per ROM file (and per EEPROM).

The Arduino speaks a small binary protocol:
    'W' <addr_lo> <addr_hi> <data>  writes a byte and replies 0x55 (ACK)
    'R' <addr_lo> <addr_hi>         replies with the single data byte

After uploading, the contents are read back and compared against the image
to verify the write (disable with --no-verify).

Example:
    python microcode_upload.py rom1.bin --port /dev/tty.usbmodem14101
"""

import argparse
import sys
import time

import serial
from serial.tools import list_ports

ACK = b"\x55"
WRITE_CMD = b"W"
READ_CMD = b"R"

# Cap how many per-byte mismatches we print during verification so a wholesale
# failure (e.g. nothing written) doesn't flood the terminal with 1024 lines.
MAX_MISMATCHES_SHOWN = 16


def _addr_bytes(addr: int) -> bytes:
    """Return the low/high address bytes for a 15-bit EEPROM address."""
    return bytes([addr & 0xFF, (addr >> 8) & 0xFF])

# Substrings that identify a likely Arduino serial port. macOS exposes USB
# CDC devices as /dev/tty.usbmodem* or /dev/tty.usbserial*; on Linux they
# show up as /dev/ttyACM* or /dev/ttyUSB*. We also match common vendor names.
PORT_HINTS = ("usbmodem", "usbserial", "ttyacm", "ttyusb", "arduino")


def detect_port() -> str:
    """Return the device path of the single likely Arduino port.

    Raises RuntimeError if zero or more than one candidate is found so the
    user can disambiguate with --port.
    """
    candidates = []
    for p in list_ports.comports():
        haystack = " ".join(
            str(s).lower() for s in (p.device, p.description, p.manufacturer)
        )
        if any(hint in haystack for hint in PORT_HINTS):
            candidates.append(p)

    if not candidates:
        raise RuntimeError(
            "No Arduino serial port found. Plug in the uploader or pass --port."
        )
    if len(candidates) > 1:
        listing = "\n".join(f"  {p.device} ({p.description})" for p in candidates)
        raise RuntimeError(
            "Multiple serial ports found; choose one with --port:\n" + listing
        )
    return candidates[0].device


def print_table(data: bytes, binary: bool = False) -> None:
    """Print a dump-style table of the data with the starting address on the
    left of each row.

    Hex mode (default) shows 16 bytes per row with an ASCII gutter. Binary
    mode shows 8 bytes per row, each as 8 bits -- more useful for microcode
    where every bit is a separate control signal.
    """
    if binary:
        width = 8
        print("addr   " + " ".join(f"{c:^8}" for c in range(width)))
        print("-" * (7 + width * 9))
        for offset in range(0, len(data), width):
            chunk = data[offset : offset + width]
            bin_part = " ".join(f"{b:08b}" for b in chunk)
            print(f"{offset:#06x} {bin_part}")
        return

    width = 16
    print("addr   " + " ".join(f"{c:02x}" for c in range(width)))
    print("-" * (7 + width * 3))
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"{offset:#06x} {hex_part:<{width * 3 - 1}}  {ascii_part}")


def verify(ser: serial.Serial, data: bytes) -> None:
    """Read the EEPROM back and compare it against the uploaded image.

    Raises RuntimeError if any byte differs or a read times out.
    """
    print("Verifying")
    mismatches = []
    for addr, expected in enumerate(data):
        ser.write(READ_CMD + _addr_bytes(addr))
        resp = ser.read(1)
        if len(resp) != 1:
            raise RuntimeError(f"Verify timed out at address {addr:#06x}")
        got = resp[0]
        if got != expected:
            mismatches.append((addr, expected, got))
        if addr % 32 == 0:
            print(".", end="", flush=True)

    if mismatches:
        print()
        for addr, expected, got in mismatches[:MAX_MISMATCHES_SHOWN]:
            print(f"  {addr:#06x}: wrote {expected:#04x}, read {got:#04x}")
        if len(mismatches) > MAX_MISMATCHES_SHOWN:
            print(f"  ... and {len(mismatches) - MAX_MISMATCHES_SHOWN} more")
        raise RuntimeError(f"Verification failed: {len(mismatches)} byte(s) differ")

    print("\nVerification OK")


def upload(
    rom_path: str,
    port: str,
    baud: int,
    verbose: bool = False,
    binary: bool = False,
    do_verify: bool = True,
) -> None:
    with open(rom_path, "rb") as f:
        data = f.read()

    if verbose:
        print_table(data, binary=binary)

    print(f"Uploading {len(data)} bytes from {rom_path} to {port} @ {baud} baud")

    with serial.Serial(port, baud, timeout=2) as ser:
        # Opening the port resets the Arduino; wait for the bootloader and
        # discard any boot noise so the byte stream stays in sync.
        time.sleep(2)
        ser.reset_input_buffer()

        for addr, byte in enumerate(data):
            ser.write(WRITE_CMD + _addr_bytes(addr) + bytes([byte]))
            resp = ser.read()
            if resp != ACK:
                raise RuntimeError(
                    f"Upload failed at address {addr:#06x}: expected {ACK!r}, "
                    f"got {resp!r}"
                )
            if addr % 32 == 0:
                print(".", end="", flush=True)

        print("\nDone")

        if do_verify:
            verify(ser, data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", help="ROM image to upload (e.g. rom1.bin)")
    parser.add_argument(
        "--port",
        default=None,
        help="Serial port of the Arduino (default: auto-detect)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=115200,
        help="Baud rate (default: %(default)s)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print a table of the uploaded data before uploading",
    )
    parser.add_argument(
        "-b",
        "--binary",
        action="store_true",
        help="With --verbose, show each byte as binary (per-bit control "
        "signals) instead of hex/ASCII",
    )
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip reading the EEPROM back to verify after uploading",
    )
    args = parser.parse_args()

    try:
        port = args.port or detect_port()
        if args.port is None:
            print(f"Auto-detected port: {port}")
        upload(args.rom, port, args.baud, args.verbose, args.binary, args.verify)
    except (OSError, serial.SerialException, RuntimeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
