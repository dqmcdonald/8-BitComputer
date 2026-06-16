"""
Microcode ROM definition.

A 32x8 array of 24-bit control words. Each row is an instruction (indexed by
the 5-bit opcode), and each column is a T-state (0-7). Values are ORed
SignalFlags control words that define which signals are asserted each step.

T0 and T1 are the fetch cycle, common to all instructions.
"""

import numpy as np

from signals import SignalFlags as SF

T0 = SF.COUO | SF.MROI  # Counter out to bus, into ROM mem register
T1 = SF.ROMO | SF.IRGI | SF.COUE  # Prog Rom Out,

# fmt: off
microcode: list[list[int]] = [
    #  T0  T1  T2  T3  T4  T5  T6  T7
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x00 NOP
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x01 LDA  - Load into Register A
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x02 LDB  - Load into Register B
    [  T0,  T1,  0,  0,  0,  0,  0,  0,  0  ],  # 0x03 ADD  - Add A and B, store result in A
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x04 STA  - Store Register A into RAM
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x05 STB  - Store Register B into RAM
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x06 JMP  - Jump to address
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x07 JMC  - Jump on carry
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x08 JMZ  - Jump on zero
    [  T0,  T1,  0,  0,  0,  0,  0,  0  ],  # 0x09 OUT  - Display contents of Register A
    [  T0,  T1,  SF.HALT,  0,  0,  0,  0,  0  ],  # 0x0A HLT  - Stop the clock
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


def write_rom(filename: str) -> None:
    """Write the microcode array to a binary file as uint32 values."""
    flat = [word for row in microcode for word in row]
    np.array(flat, dtype=np.uint32).tofile(filename)
