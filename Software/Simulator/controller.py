"""

The controller makes signal state available to all other modules
and the clock. Modules register to check signals but this is largely to
allow us to know what is connected to what and be able to report on it.

"""

import logging
from typing import Callable

import numpy as np

from instructions import InstructionSet
from signals import SIGNAL_MAP, Signal, decode

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, size1: int, size2: int, romfile1: str, romfile2: str) -> None:
        """
        Takes two sizes and two filenames, ont for the each of the
        ROMs used in the controller, modelled here by Numpy arrays
        """
        self._registered_modules = {}  # List of signals registered by module name
        self._signal_state = {sig: False for sig in Signal}
        self._rom1 = self.readRomFile(romfile1, size1)
        self._rom2 = self.readRomFile(romfile2, size2)
        self._t_state: int = 0
        self._instruction_source: Callable[[], int] | None = None
        self._flags_source: Callable[[], int] | None = None

    def readRomFile(self, contents_file: str, size: int):
        """
        Read rt
        """
        if len(contents_file) > 0:
            raw = np.fromfile(contents_file, dtype=np.uint8)
            if len(raw) > size // 8:
                raise ValueError(
                    f"ROM File too large for memory ({len(raw)} > {size} bytes)"
                )
        else:
            raw = np.zeros(size // 8, dtype=np.uint8)
        return raw

    def clear(self):
        self._signal_state = dict.fromkeys(self._signal_state, False)

    def registerForSignal(self, module_name: str, signal: Signal):
        """
        Allows modules to register for signals. This tells us what is
        connected and also allows for early checking of unknown signals.
        Modules cannot query signal state of signals they have not registered
        for.
        """
        if not isinstance(signal, Signal):
            raise TypeError(f"{signal!r} is not a Signal enum member")

        if module_name in self._registered_modules:
            if signal in self._registered_modules[module_name]:
                raise ValueError(
                    f"Module {module_name} has already registered for signal {signal.name}"
                )
        else:
            self._registered_modules[module_name] = []
        self._registered_modules[module_name].append(signal)
        logger.info("'%s' registered for signal '%s'", module_name, signal.name)

    def getSignalState(self, module_name: str, signal: Signal) -> bool:
        """
        Return the state of the named signal to the named module
        """
        if not isinstance(signal, Signal):
            raise TypeError(f"{signal!r} is not a Signal enum member")

        if module_name not in self._registered_modules:
            raise ValueError(f"{module_name} is not registered for {signal.name}")

        state = self._signal_state[signal]
        logger.debug("'%s' queried signal '%s' -> %s", module_name, signal.name, state)
        return state

    def setInstructionSource(self, source: Callable[[], int]) -> None:
        """Register a callable that returns the current instruction register value."""
        self._instruction_source = source

    def setFlagsSource(self, source: Callable[[], int]) -> None:
        """Register a callable that returns the 2-bit flag state (bit1=zero, bit0=carry)."""
        self._flags_source = source

    def clock_pulse(self):
        self.clear()

        if self._instruction_source is None:
            logger.debug("Controller: no instruction source — signals cleared")
            return

        instruction = self._instruction_source() & 0x1F  # 5-bit opcode
        flags = self._flags_source() & 0x03 if self._flags_source else 0  # 2-bit flag state
        # 10-bit ROM address: [flags(9:8) | instruction(7:3) | t_state(2:0)]
        address = (flags << 8) | (instruction << 3) | self._t_state

        rom1_byte = int(self._rom1[address])
        rom2_byte = int(self._rom2[address])

        try:
            instr_name = InstructionSet(instruction).name
        except ValueError:
            instr_name = "???"

        logger.debug(
            "Controller: t=%d instr=0x%02X (%s) flags=%d addr=%d  ROM1=0x%02X ROM2=0x%02X",
            self._t_state, instruction, instr_name, flags, address, rom1_byte, rom2_byte,
        )

        enc_lower    = rom1_byte & 0x07
        lower_direct = (rom1_byte >> 3) & 0x1F   # 5 bits: RAMI, COUE, COUO, FLGI, HALT
        enc_upper    = rom2_byte & 0x07
        upper_direct = (rom2_byte >> 3) & 0x1F

        # enc=0 means no signal in this decoder group (not signal 0)
        lower_onehot = decode(enc_lower) if enc_lower != 0 else 0
        upper_onehot = decode(enc_upper) if enc_upper != 0 else 0

        control_word = (
            lower_onehot
            | (lower_direct << 8)
            | (upper_onehot << 13)
            | (upper_direct << 21)
        )

        active = []
        for flag, sig in SIGNAL_MAP.items():
            if control_word & int(flag):
                self._signal_state[sig] = True
                active.append(sig.name)

        if active:
            logger.info(
                "Controller: t=%d instr=0x%02X (%s)  active signals: %s",
                self._t_state, instruction, instr_name, ", ".join(active),
            )
        else:
            logger.debug(
                "Controller: t=%d instr=0x%02X (%s)  no signals active",
                self._t_state, instruction, instr_name,
            )

    def getTState(self) -> int:
        return self._t_state

    def getConnections(self) -> dict:
        """Return a copy of the module→signals registration map."""
        return {name: list(sigs) for name, sigs in self._registered_modules.items()}

    def getSignalStates(self) -> dict:
        """Return a copy of the current signal-state dict."""
        return dict(self._signal_state)

    def reset(self) -> None:
        self.clear()
        self._t_state = 0
        logger.debug("Controller: reset")

    def clock_inv_pulse(self):
        if self._signal_state[Signal.TRES]:
            self._t_state = 0
            logger.info("Controller: t_state reset to 0 (TRES)")
        else:
            self._t_state = (self._t_state + 1) & 0x07
            logger.debug("Controller: t_state now %d", self._t_state)
