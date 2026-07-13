"""Upload a user program to the AT28C64 EEPROM on the ProgramROM board.

Programs come from Assembler/assembler.py (e.g. test.bin) and are at most 256
bytes -- the 8-bit address space the computer's program counter can reach.

The ProgramROM board holds 32 such programs, one per 256-byte "bank". The bank
is chosen by the 5-way DIP switch (SW1) on the board, which drives EEPROM lines
A8-A12 directly. The Arduino has no control over it, so:

    >>> SET THE DIP SWITCH TO THE BANK YOU WANT BEFORE RUNNING THIS <<<

You run and flash the same slot, so whatever the DIP is set to is both where
this writes and what the computer will execute.

The Arduino (Software/ProgramUploader) speaks a small binary protocol:
    '?'                -> b"PRG1"  identify
    'P'                -> 0x55     enter PROGRAM mode (asserts PROG + HALT)
    'X'                -> 0x55     exit to RUN mode
    'W' <addr> <data>  -> 0x55 ACK, or 0x4E NAK if the write timed out
    'R' <addr>         -> <data>

The address is one byte here, unlike microcode_upload.py's two -- hence the '?'
handshake, which makes sure we are talking to the program uploader and not the
microcode uploader (both understand 'W'/'R', so without it a mixup would just
silently write garbage).

Programming asserts HALT and stops the computer's clock for the duration. The
board is always handed back to the computer on the way out, even if the upload
fails.

By default the program is padded out to a full 256 bytes so the rest of the bank
is left in a known state rather than holding fragments of whatever was flashed
there before. The pad byte is 0x00 (NOP); --fill 0x0c (HLT) instead if you would
rather the computer stop when it runs off the end of your program.

After uploading, the bank is read back and compared against the image (disable
with --no-verify).

Example:
    python program_upload.py ../Assembler/test.bin --port /dev/tty.usbmodem14101
"""

import argparse
import sys
import time

import serial

# detect_port and print_table are protocol-agnostic -- share them with the
# microcode uploader rather than keeping two copies in step.
from microcode_upload import detect_port, print_table

ACK = b"\x55"
NAK = b"\x4e"
IDENT = b"PRG1"

IDENTIFY_CMD = b"?"
ENTER_CMD = b"P"
EXIT_CMD = b"X"
WRITE_CMD = b"W"
READ_CMD = b"R"

# One bank = 256 bytes = everything the 8-bit program counter can address.
BANK_SIZE = 256

# Cap how many per-byte mismatches we print during verification so a wholesale
# failure (e.g. nothing written) doesn't flood the terminal with 256 lines.
MAX_MISMATCHES_SHOWN = 16


def identify(ser: serial.Serial) -> None:
    """Confirm the Arduino is running the program uploader sketch.

    Raises RuntimeError if it answers with anything else -- most likely the
    microcode uploader, which shares the 'W'/'R' commands but takes a two-byte
    address and would misparse everything we sent it.
    """
    ser.write(IDENTIFY_CMD)
    resp = ser.read(len(IDENT))
    if resp != IDENT:
        raise RuntimeError(
            f"Unexpected reply to identify: got {resp!r}, expected {IDENT!r}. "
            "Is the Arduino running Software/ProgramUploader? (The microcode "
            "uploader sketch will not answer this.)"
        )


def enter_program_mode(ser: serial.Serial) -> None:
    """Put the board in PROGRAM mode: asserts PROG and HALTs the computer."""
    ser.write(ENTER_CMD)
    if ser.read(1) != ACK:
        raise RuntimeError("Arduino did not acknowledge entering PROGRAM mode")


def exit_program_mode(ser: serial.Serial) -> None:
    """Return the board to RUN mode and let the computer's clock go again."""
    ser.write(EXIT_CMD)
    if ser.read(1) != ACK:
        raise RuntimeError("Arduino did not acknowledge returning to RUN mode")


def write_image(ser: serial.Serial, data: bytes) -> None:
    """Write every byte of "data" into the DIP-selected bank."""
    for addr, byte in enumerate(data):
        ser.write(WRITE_CMD + bytes([addr, byte]))
        resp = ser.read(1)
        if resp == NAK:
            raise RuntimeError(
                f"EEPROM write timed out at address {addr:#04x}. The AT28C64 "
                "never finished its write cycle -- check the board is powered "
                "and the programming header is seated."
            )
        if resp != ACK:
            raise RuntimeError(
                f"Upload failed at address {addr:#04x}: expected {ACK!r}, "
                f"got {resp!r}"
            )
        if addr % 32 == 0:
            print(".", end="", flush=True)


def read_image(ser: serial.Serial, size: int) -> bytes:
    """Read "size" bytes back out of the DIP-selected bank."""
    out = bytearray()
    for addr in range(size):
        ser.write(READ_CMD + bytes([addr]))
        resp = ser.read(1)
        if len(resp) != 1:
            raise RuntimeError(f"Read timed out at address {addr:#04x}")
        out += resp
        if addr % 32 == 0:
            print(".", end="", flush=True)
    return bytes(out)


def verify(ser: serial.Serial, data: bytes) -> None:
    """Read the bank back and compare it against the uploaded image."""
    print("Verifying")
    actual = read_image(ser, len(data))

    mismatches = [
        (addr, expected, got)
        for addr, (expected, got) in enumerate(zip(data, actual))
        if expected != got
    ]

    if mismatches:
        print()
        for addr, expected, got in mismatches[:MAX_MISMATCHES_SHOWN]:
            print(f"  {addr:#04x}: wrote {expected:#04x}, read {got:#04x}")
        if len(mismatches) > MAX_MISMATCHES_SHOWN:
            print(f"  ... and {len(mismatches) - MAX_MISMATCHES_SHOWN} more")
        raise RuntimeError(f"Verification failed: {len(mismatches)} byte(s) differ")

    print("\nVerification OK")


def load_image(path: str, fill: int, pad: bool) -> bytes:
    """Read the program image and pad it out to a full bank."""
    with open(path, "rb") as f:
        data = f.read()

    if len(data) > BANK_SIZE:
        raise RuntimeError(
            f"{path} is {len(data)} bytes, which exceeds the {BANK_SIZE}-byte "
            "program space (the computer's address bus is only 8 bits wide)"
        )
    if not data:
        raise RuntimeError(f"{path} is empty")

    if pad and len(data) < BANK_SIZE:
        data += bytes([fill]) * (BANK_SIZE - len(data))
    return data


def upload(
    rom_path: str,
    port: str,
    baud: int,
    verbose: bool = False,
    do_verify: bool = True,
    fill: int = 0x00,
    pad: bool = True,
) -> None:
    data = load_image(rom_path, fill, pad)

    if verbose:
        print_table(data)

    print(f"Uploading {len(data)} bytes from {rom_path} to {port} @ {baud} baud")
    print("Programming the bank currently selected by the DIP switch (SW1).")

    with serial.Serial(port, baud, timeout=2) as ser:
        # Opening the port resets the Arduino; wait for the bootloader and
        # discard any boot noise so the byte stream stays in sync.
        time.sleep(2)
        ser.reset_input_buffer()

        identify(ser)
        enter_program_mode(ser)
        print("Board in PROGRAM mode (computer halted)")
        try:
            write_image(ser, data)
            print("\nDone")

            if do_verify:
                verify(ser, data)
        finally:
            # Always give the computer its ROM and its clock back, even if the
            # upload or the verify blew up part way through.
            exit_program_mode(ser)
            print("Board returned to RUN mode")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("program", help="Program image to upload (e.g. test.bin)")
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
        help="Print a table of the program image before uploading",
    )
    parser.add_argument(
        "--fill",
        type=lambda s: int(s, 0),
        default=0x00,
        help="Byte used to pad the program out to a full 256-byte bank "
        "(default: 0x00, NOP; try 0x0c for HLT)",
    )
    parser.add_argument(
        "--no-pad",
        dest="pad",
        action="store_false",
        help="Write only the program's own bytes and leave the rest of the "
        "bank as it was, instead of padding to 256 bytes",
    )
    parser.add_argument(
        "--no-verify",
        dest="verify",
        action="store_false",
        help="Skip reading the EEPROM back to verify after uploading",
    )
    args = parser.parse_args()

    if not 0 <= args.fill <= 0xFF:
        print(f"Error: --fill must be a byte (0-255), got {args.fill}", file=sys.stderr)
        return 1

    try:
        port = args.port or detect_port()
        if args.port is None:
            print(f"Auto-detected port: {port}")
        upload(
            args.program,
            port,
            args.baud,
            args.verbose,
            args.verify,
            args.fill,
            args.pad,
        )
    except (OSError, serial.SerialException, RuntimeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
