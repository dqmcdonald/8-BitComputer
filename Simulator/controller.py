"""

The controller makes signal state available to all other modules
and the clock. Modules register to check signals but this is largely to
allow us to know what is connected to what and be able to report on it.

"""

import logging
from csv import reader

import numpy as np

from signals import Signal, active_signals

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self, size1: int, size2: int, romfile1: str, romfile2: str) -> None:
        """
        Takes two sizes and two filenames, ont for the each of the
        ROMs used in the controller, modelled here by Numpy arrays
        """
        self._registered_modules = {}  # List of signals registered by module name
        self._signal_state = {sig: False for sig in Signal}
        self._signal_flags = {}
        self._rom1 = self.readRomFile(romfile1, size1)
        self._rom2 = self.readRomFile(romfile2, size2)

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

    def clock_pulse(self):
        logger.debug("Controller: clock pulse")
        self.clear()  # all signals → False
        # Need to get active signals from the microcode here:

    #        for sig in active_signals(0b100000000000000000000000):
    #            logger.debug(f"Controller: turning on signal {sig.name}")
    #            self._signal_state[sig] = True

    def clock_inv_pulse(self):
        logger.debug("Controller: clock inv pulse")
