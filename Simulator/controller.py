"""

The controller makes signal state available to all other modules
and the clock. Modules register to check signals but this is largely to
allow us to know what is connected to what and be able to report on it.

"""

import logging

from signals import Signal

logger = logging.getLogger(__name__)


class Controller:
    def __init__(self) -> None:
        self._registered_modules = {}  # List of signals registered by module name
        self._signal_state = {sig: False for sig in Signal}

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

    def clock_inv_pulse(self):
        logger.debug("Controller: clock inv pulse")
