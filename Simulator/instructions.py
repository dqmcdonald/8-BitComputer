""" "
Defines the instruction set for the 8-Bit computer


"""

from enum import IntFlag


class InstructionSet(IntFlag):
    NOP = 0b00000  # NoOp
    LDA = 0b00001  # Load into Register A
    LDB = 0b00010  # Load into Register B
    ADD = 0b00011  # Add register A and B, store result in A
    STA = 0b00100  # Store register A into RAM
    STB = 0b00101  # Store register B into RAM
    JMP = 0b00110  # Jump to address
    JMC = 0b00111  # Jump on carry
    JMZ = 0b01000  # Jump on zero
    OUT = 0b01001  # Display the contents of register A
    HLT = 0b01010  # Stop the clock (and the program)
