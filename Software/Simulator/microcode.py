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

T0 = SF.COUO | SF.MROI             # Fetch: PC → ProgROM addr reg
T1 = SF.ROMO | SF.IRGI | SF.COUE  # Fetch: ROM[PC] → IR, PC++
LO = SF.ROMO | SF.MRAI | SF.COUE  # Load operand: ROM[PC] → MAR, PC++
TR = SF.TRES                        # Reset t-state counter

# Flag state indices: bits are [zero, carry], so carry=bit0, zero=bit1
FLAGS_Z0C0 = 0  # zero=0, carry=0
FLAGS_Z0C1 = 1  # zero=0, carry=1
FLAGS_Z1C0 = 2  # zero=1, carry=0
FLAGS_Z1C1 = 3  # zero=1, carry=1

# Jump opcode indices (must match InstructionSet values)
_JMC = 0x09
_JMZ = 0x0A

# Instructions with an operand byte use T0 again at T2 to re-fetch PC into
# ProgROMReg, then consume the operand byte at T3 before the operation at T4.
# fmt: off
UCODE_TEMPLATE: list[list[int]] = [
    #  T0   T1   T2   T3                      T4                       T5   T6  T7
    [  T0,  T1,  TR,  0,                       0,                       0,   0,  0  ],  # 0x00 NOP
    [  T0,  T1,  T0,  LO,                      SF.RAMO|SF.ARGI,        TR,   0,  0  ],  # 0x01 LDA  - Load A from RAM[operand]
    [  T0,  T1,  T0,  LO,                      SF.RAMO|SF.BRGI,        TR,   0,  0  ],  # 0x02 LDB  - Load B from RAM[operand]
    [  T0,  T1,  SF.ALUO|SF.ARGI|SF.FLGI,     TR,                      0,    0,  0,  0  ],  # 0x03 ADD  - A = A + B, latch flags
    [  T0,  T1,  SF.ALUO|SF.ARGI|SF.FLGI|SF.SUBT, TR,                  0,    0,  0,  0  ],  # 0x04 SUB  - A = A - B, latch flags
    [  T0,  T1,  T0,  SF.ROMO|SF.ARGI|SF.COUE, TR,                     0,    0,  0  ],  # 0x05 LDAI - Load A with immediate operand
    [  T0,  T1,  T0,  LO,                      SF.ARGO|SF.RAMI,        TR,   0,  0  ],  # 0x06 STA  - RAM[operand] = A
    [  T0,  T1,  T0,  LO,                      SF.BRGO|SF.RAMI,        TR,   0,  0  ],  # 0x07 STB  - RAM[operand] = B
    [  T0,  T1,  T0,  SF.ROMO|SF.JUMP,         TR,                     0,    0,  0  ],  # 0x08 JMP  - PC = operand
    [  T0,  T1,  T0,  SF.COUE,                 TR,                     0,    0,  0  ],  # 0x09 JMC  - Jump on carry (default: skip operand)
    [  T0,  T1,  T0,  SF.COUE,                 TR,                     0,    0,  0  ],  # 0x0A JMZ  - Jump on zero  (default: skip operand)
    [  T0,  T1,  SF.ARGO|SF.OUTI,  TR,  0,  0,  0,  0  ],  # 0x0B OUT  - Display contents of Register A
    [  T0,  T1,  SF.HALT,  TR,  0,  0,  0,  0  ],  # 0x0C HLT  - Stop the clock
    [  T0,  T1,  T0,  SF.ROMO|SF.BRGI|SF.COUE, TR,                     0,    0,  0  ],  # 0x0D LDBI - Load B with immediate operand
    [  T0,  T1,  T0,  SF.ROMO|SF.BRGI|SF.COUE, SF.ALUO|SF.ARGI|SF.FLGI,         TR,  0,  0  ],  # 0x0E ADDI - A = A + immediate (clobbers B)
    [  T0,  T1,  T0,  SF.ROMO|SF.BRGI|SF.COUE, SF.ALUO|SF.ARGI|SF.FLGI|SF.SUBT, TR,  0,  0  ],  # 0x0F SUBI - A = A - immediate (clobbers B)
    [  T0,  T1,  SF.FLGI|SF.SUBT,                TR,  0,  0,  0,  0  ],  # 0x10 CMP  - set flags from A-B, leave A unchanged
    [  T0,  T1,  T0,  SF.ROMO|SF.BRGI|SF.COUE, SF.FLGI|SF.SUBT, TR,  0,  0  ],  # 0x11 CMPI - set flags from A-immediate, leave A unchanged
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


def _build_microcode() -> list[list[list[int]]]:
    """Build the 4×32×8 microcode table (flag_state × instruction × t-state).

    Start with four identical copies of UCODE_TEMPLATE, then override T3 of
    JMC/JMZ in the flag variants where the condition is met.  The default T3
    for both is COUE (advance PC past the unused operand byte); when the
    condition fires it becomes ROMO|JUMP (load PC from the operand byte).
    """
    import copy
    mc = [copy.deepcopy(UCODE_TEMPLATE) for _ in range(4)]

    jump_t3 = int(SF.ROMO | SF.JUMP)

    # JMC fires when carry is set (C=1): flag indices 1 and 3
    for fi in (FLAGS_Z0C1, FLAGS_Z1C1):
        mc[fi][_JMC][3] = jump_t3

    # JMZ fires when zero is set (Z=1): flag indices 2 and 3
    for fi in (FLAGS_Z1C0, FLAGS_Z1C1):
        mc[fi][_JMZ][3] = jump_t3

    return mc


microcode: list[list[list[int]]] = _build_microcode()


def _encode_word(word: int) -> tuple[int, int]:
    """Split a control word into two ROM bytes matching the hardware layout.

    ROM1: [HALT | FLGI | COUO | COUE | RAMI | enc2:enc0]  (bits 7:3:2:1:0)
    ROM2: [SUBT | enc2:enc0]
    """
    lower_decoder = word & 0xFF           # bits 0-7:   decoder group 1 one-hot
    lower_direct  = (word >> 8) & 0x1F   # bits 8-12:  RAMI, COUE, COUO, FLGI, HALT
    upper_decoder = (word >> 13) & 0xFF  # bits 13-20: decoder group 2 (bit 13 = Y0 reserved)
    upper_direct  = (word >> 21) & 0x1F  # bits 21+:   SUBT, ...

    enc_lower = encode(lower_decoder) or 0
    enc_upper = encode(upper_decoder) or 0

    return (lower_direct << 3) | enc_lower, (upper_direct << 3) | enc_upper


def write_roms(rom1_file: str = "rom1.bin", rom2_file: str = "rom2.bin") -> None:
    """Encode the microcode table and write it to two ROM binary files.

    10-bit ROM address: [flags(9:8) | instruction(7:3) | t_state(2:0)]
    giving 4 × 32 × 8 = 1024 entries per ROM file.
    """
    rom1, rom2 = [], []
    for flag_state in range(4):
        for instr in range(32):
            if len(microcode[flag_state][instr]) != 8:
                raise ValueError(
                    f"Microcode row [{flag_state}][{instr}] has wrong length "
                    f"(expected 8, got {len(microcode[flag_state][instr])})"
                )
            for word in microcode[flag_state][instr]:
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
