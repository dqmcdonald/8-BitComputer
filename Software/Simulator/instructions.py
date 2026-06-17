""" "
Defines the instruction set for the 8-Bit computer


"""

from enum import IntEnum


class InstructionSet(IntEnum):
    NOP = 0b00000  # NoOp
    LDA = 0b00001  # Load into Register A
    LDB = 0b00010  # Load into Register B
    ADD = 0b00011  # Add register A and B, store result in A
    SUB = 0b00100  # Subtract register B from A, store result in A
    LDAI = 0b00101  # Load immediate value into A
    LDBI = 0b01101  # Load immediate value into B
    ADDI = 0b01110  # Add immediate value to A (clobbers B)
    SUBI = 0b01111  # Subtract immediate value from A (clobbers B)
    STA = 0b00110  # Store register A into RAM
    STB = 0b00111  # Store register B into RAM
    JMP = 0b01000  # Jump to address
    JMC = 0b01001  # Jump on carry
    JMZ = 0b01010  # Jump on zero
    OUT = 0b01011  # Display the contents of register A
    HLT = 0b01100  # Stop the clock (and the program)
