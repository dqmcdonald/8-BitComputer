from enum import Enum, IntFlag, auto


class Signal(Enum):
    CLEA = auto()  # Clear: reset all registers to zero
    JUMP = auto()  # Jump: load the program counter from the bus
    MROI = auto()  # Program memory register in
    MRAI = auto()  # Ram memory register in
    ARGI = auto()  # Register A In: load register A from the bus
    BRGI = auto()  # Register B In: load register B from the bus
    IRGI = auto()  # Instruction Register In: load the instruction register from the bus
    OUTI = auto()  # Output register input (there is no output)
    RAMI = auto()  # RAM In: write the bus value into RAM at the current address
    COUE = auto()  # Counter enable: advance the program counter
    COUO = auto()  # Counter out: drive the program counter onto the bus
    FLGI = auto()  # Flags In: latch the ALU carry and zero flags into the flags register
    ARGO = auto()  # Register A Out: drive register A onto the bus
    BRGO = auto()  # Register B Out: drive register B onto the bus
    ROMO = auto()  # Output the value from the program rom
    RAMO = auto()  # Drive the ram to the bus
    TRES = auto()  # Step counter reset
    ALUO = auto()  # Adder out to bus
    IRGO = auto()  # Instruction Register Out: drive the instruction register onto the bus
    HALT = auto()  # Halt: stop the clock
    SUBT = auto()  # Subtract: ALU computes A - B instead of A + B


class SignalFlags(IntFlag):
    # Decoder group 1 (bits 0-7): one-hot via HC138, address 1-7 usable (0 = no signal)
    CLEA = 0b000000000000000000000001  # bit  0 — not used in microcode (hardware reset only)
    JUMP = 0b000000000000000000000010  # bit  1
    MROI = 0b000000000000000000000100  # bit  2
    MRAI = 0b000000000000000000001000  # bit  3
    ARGI = 0b000000000000000000010000  # bit  4
    BRGI = 0b000000000000000000100000  # bit  5
    IRGI = 0b000000000000000001000000  # bit  6
    OUTI = 0b000000000000000010000000  # bit  7
    # Direct group 1 (bits 8-11)
    RAMI = 0b000000000000000100000000  # bit  8
    COUE = 0b000000000000001000000000  # bit  9
    COUO = 0b000000000000010000000000  # bit 10
    FLGI = 0b000000000000100000000000  # bit 11
    # Decoder group 2 (bits 12-19): one-hot via HC138, address 1-7 usable (0 = no signal)
    # HALT occupies the no-signal slot (bit 12 / address 0) and is routed directly to ROM1 bit 7
    HALT = 0b000000000001000000000000  # bit 12 → ROM1 bit 7
    ARGO = 0b000000000010000000000000  # bit 13
    BRGO = 0b000000000100000000000000  # bit 14
    ROMO = 0b000000001000000000000000  # bit 15
    RAMO = 0b000000010000000000000000  # bit 16
    TRES = 0b000000100000000000000000  # bit 17
    ALUO = 0b000001000000000000000000  # bit 18
    IRGO = 0b000010000000000000000000  # bit 19
    # Direct group 2 (bits 20-23) → ROM2 bits 3-6
    SUBT = 0b000100000000000000000000  # bit 20 → ROM2 bit 3


SIGNAL_MAP: dict[SignalFlags, Signal] = {
    SignalFlags.CLEA: Signal.CLEA,
    SignalFlags.JUMP: Signal.JUMP,
    SignalFlags.MROI: Signal.MROI,
    SignalFlags.MRAI: Signal.MRAI,
    SignalFlags.ARGI: Signal.ARGI,
    SignalFlags.BRGI: Signal.BRGI,
    SignalFlags.IRGI: Signal.IRGI,
    SignalFlags.OUTI: Signal.OUTI,
    SignalFlags.RAMI: Signal.RAMI,
    SignalFlags.COUE: Signal.COUE,
    SignalFlags.COUO: Signal.COUO,
    SignalFlags.FLGI: Signal.FLGI,
    SignalFlags.HALT: Signal.HALT,
    SignalFlags.ARGO: Signal.ARGO,
    SignalFlags.BRGO: Signal.BRGO,
    SignalFlags.ROMO: Signal.ROMO,
    SignalFlags.RAMO: Signal.RAMO,
    SignalFlags.TRES: Signal.TRES,
    SignalFlags.ALUO: Signal.ALUO,
    SignalFlags.IRGO: Signal.IRGO,
    SignalFlags.SUBT: Signal.SUBT,
}


def active_signals(state: int) -> list[Signal]:
    """Return the list of Signals whose flag bits are set in state."""
    return [sig for flag, sig in SIGNAL_MAP.items() if state & flag]


def decode(address: int) -> int:
    """Convert a 3-bit address (0-7) to a one-hot 8-bit value."""
    if not (0 <= address <= 7):
        return 0x00
    return 1 << address


def encode(outputs: int) -> int | None:
    """Convert a one-hot 8-bit value to a 3-bit address. Returns None if invalid."""
    if outputs == 0 or (outputs & (outputs - 1)) != 0:
        return None
    return outputs.bit_length() - 1
