from enum import Enum, auto


class Signal(Enum):
    CLEA = auto()  # Clear: reset all registers to zero
    HALT = auto()  # Halt: stop the clock
    RAIN = auto()  # Register A In: load register A from the bus
    RAOU = auto()  # Register A Out: drive register A onto the bus
    RBIN = auto()  # Register B In: load register B from the bus
    RBOU = auto()  # Register B Out: drive register B onto the bus
    IRIN = auto()  # Instruction Register In: load the instruction register from the bus
    IROU = (
        auto()
    )  # Instruction Register Out: drive the instruction register onto the bus
    RAMI = auto()  # RAM In: write the bus value into RAM at the current address
    RAMO = auto()  # RAM Out: drive the RAM value at the current address onto the bus
    ALUO = auto()  # ALU Out: drive the ALU result onto the bus
    SUBT = auto()  # Subtract: ALU computes A - B instead of A + B
    FLGI = (
        auto()
    )  # Flags In: latch the ALU carry and zero flags into the flags register
    MIIN = (
        auto()
    )  # Memory Address Register In: load the memory address register from the bus
    MIOU = (
        auto()
    )  # Memory Address Register Out: drive the memory address register onto the bus
    JUMP = auto()  # Jump: load the program counter from the bus
    PCOU = auto()  # Program Counter Out: drive the program counter value onto the bus
    ORIN = auto()  # Output register input (there is no output)
