"""
Microcode ROM definition.

A 32x8 array of 24-bit control words. Each row is an instruction (indexed by
the 5-bit opcode), and each column is a T-state (0-7). Values are ORed
SignalFlags control words that define which signals are asserted each step.

T0 and T1 are the fetch cycle, common to all instructions.
"""

import numpy as np

from signals import SignalFlags as SF

# fmt: off
microcode: list[list[int]] = [
    #  T0  T1  T2  T3  T4  T5  T6  T7
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x00 NOP
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x01 LDA  - Load into Register A
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x02 LDB  - Load into Register B
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x03 ADD  - Add A and B, store result in A
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x04 STA  - Store Register A into RAM
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x05 STB  - Store Register B into RAM
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x06 JMP  - Jump to address
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x07 JMC  - Jump on carry
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x08 JMZ  - Jump on zero
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x09 OUT  - Display contents of Register A
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x0A HLT  - Stop the clock
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x0B (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x0C (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x0D (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x0E (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x0F (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x10 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x11 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x12 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x13 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x14 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x15 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x16 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x17 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x18 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x19 (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x1A (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x1B (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x1C (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x1D (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x1E (undefined)
    [  0,  0,  0,  0,  0,  0,  0,  0  ],  # 0x1F (undefined)
]
# fmt: on


def write_rom(filename: str) -> None:
    """Write the microcode array to a binary file as uint32 values."""
    flat = [word for row in microcode for word in row]
    np.array(flat, dtype=np.uint32).tofile(filename)
