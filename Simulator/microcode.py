"""
Microcode ROM definition.

A 32x8 array of 24-bit control words. Each row is an instruction (indexed by
the 5-bit opcode), and each column is a T-state (0-7). Values are ORed
SignalFlags control words that define which signals are asserted each step.

T0 and T1 are the fetch cycle, common to all instructions.
"""

import argparse

import numpy as np

from signals import SignalFlags as SF
from signals import encode

T0 = SF.COUO | SF.MROI  # Counter out to bus, into ROM mem register
T1 = SF.ROMO | SF.IRGI | SF.COUE  # Prog Rom Out,
TR = SF.TRES

# fmt: off
microcode: list[list[int]] = [
    #  T0  T1  T2  T3  T4  T5  T6  T7
    [  T0,  T1,  TR,  0,  0,  0,  0,  0  ],  # 0x00 NOP
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x01 LDA  - Load into Register A
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x02 LDB  - Load into Register B
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x03 ADD  - Add A and B, store result in A
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x04 STA  - Store Register A into RAM
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x05 STB  - Store Register B into RAM
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x06 JMP  - Jump to address
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x07 JMC  - Jump on carry
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x08 JMZ  - Jump on zero
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x09 OUT  - Display contents of Register A
    [  T0,  T1,  SF.HALT,  TR,  0,  0,  0,  0  ],  # 0x0A HLT  - Stop the clock
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x0B (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x0C (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x0D (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x0E (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x0F (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x10 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x11 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x12 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x13 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x14 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x15 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x16 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x17 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x18 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x19 (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x1A (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x1B (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x1C (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x1D (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x1E (undefined)
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x1F (undefined)
]
# fmt: on


def _encode_word(word: int) -> tuple[int, int]:
    """Split a 24-bit control word into two ROM bytes.

    ROM1: bits 0-7 HC138-encoded to 3 bits, bits 8-11 direct → byte [B11:B8, enc2:enc0]
    ROM2: bits 12-19 HC138-encoded to 3 bits, bits 20-23 direct → byte [B23:B20, enc2:enc0]
    """
    lower_decoder = word & 0xFF
    lower_direct = (word >> 8) & 0x0F
    upper_decoder = (word >> 12) & 0xFF
    upper_direct = (word >> 20) & 0x0F

    enc_lower = encode(lower_decoder) or 0
    enc_upper = encode(upper_decoder) or 0

    return (lower_direct << 3) | enc_lower, (upper_direct << 3) | enc_upper


def write_roms(rom1_file: str = "rom1.bin", rom2_file: str = "rom2.bin") -> None:
    """Encode the microcode array and write it to two ROM binary files."""
    if any(len(row) != 8 for row in microcode):
        bad = [i for i, row in enumerate(microcode) if len(row) != 8]
        raise ValueError(f"Microcode rows with wrong length (expected 8): {bad}")

    rom1, rom2 = [], []
    for row in microcode:
        for word in row:
            b1, b2 = _encode_word(int(word))
            rom1.append(b1)
            rom2.append(b2)

    np.array(rom1, dtype=np.uint8).tofile(rom1_file)
    np.array(rom2, dtype=np.uint8).tofile(rom2_file)
    print(f"Wrote {len(rom1)} bytes to {rom1_file} and {rom2_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Encode microcode and write ROM files")
    parser.add_argument(
        "--rom1",
        default="rom1.bin",
        metavar="FILE",
        help="Output file for ROM 1 (default: rom1.bin)",
    )
    parser.add_argument(
        "--rom2",
        default="rom2.bin",
        metavar="FILE",
        help="Output file for ROM 2 (default: rom2.bin)",
    )
    args = parser.parse_args()
    write_roms(args.rom1, args.rom2)
