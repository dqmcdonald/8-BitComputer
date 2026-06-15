from enum import Enum, IntFlag, auto


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


class SignalFlags(IntFlag):
    HALT = 0b100000000000000000000000
    RAIN = 0b010000000000000000000000
    RAOU = 0b001000000000000000000000
    RBIN = 0b000100000000000000000000
    RBOU = 0b000010000000000000000000
    IRIN = 0b000001000000000000000000
    IROU = 0b000000100000000000000000
    RAMI = 0b000000010000000000000000
    RAMO = 0b000000001000000000000000
    ALUO = 0b000000000100000000000000
    SUBT = 0b000000000010000000000000
    FLGI = 0b000000000001000000000000
    MIIN = 0b000000000000100000000000
    MIOU = 0b000000000000010000000000
    JUMP = 0b000000000000001000000000
    PCOU = 0b000000000000000100000000
    ORIN = 0b000000000000000010000000


SIGNAL_MAP: dict[SignalFlags, Signal] = {
    SignalFlags.HALT: Signal.HALT,
    SignalFlags.RAIN: Signal.RAIN,
    SignalFlags.RAOU: Signal.RAOU,
    SignalFlags.RBIN: Signal.RBIN,
    SignalFlags.RBOU: Signal.RBOU,
    SignalFlags.IRIN: Signal.IRIN,
    SignalFlags.IROU: Signal.IROU,
    SignalFlags.RAMI: Signal.RAMI,
    SignalFlags.RAMO: Signal.RAMO,
    SignalFlags.ALUO: Signal.ALUO,
    SignalFlags.SUBT: Signal.SUBT,
    SignalFlags.FLGI: Signal.FLGI,
    SignalFlags.MIIN: Signal.MIIN,
    SignalFlags.MIOU: Signal.MIOU,
    SignalFlags.JUMP: Signal.JUMP,
    SignalFlags.PCOU: Signal.PCOU,
    SignalFlags.ORIN: Signal.ORIN,
}


def active_signals(state: int) -> list[Signal]:
    """Return the list of Signals whose flag bits are set in state."""
    return [sig for flag, sig in SIGNAL_MAP.items() if state & flag]
