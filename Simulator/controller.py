"""

The controller makes signal state available to all other modules
and the clock. Modules register to check signals but this is largely to
allow us to know what is connected to what and be able to report on it.

"""

import logging

logger = logging.getLogger(__name__)

signals = set(
    ["CLEA", "HALT", "RAIN", "RAOU", "RBIN", "RBOU", "IRIN", "IROU", "RAMI", "RAMO"]
)


class Controller:
    def __init__(self) -> None:
        self._registered_modules = {}  # List of signals registered by module name
        self._signal_state = {}  # Boolean signal state keyed by name
        for m in signals:
            self._signal_state[m] = False

    def clear(self):
        self._signal_state = dict.fromkeys(self._signal_state, False)

    def registerForSignal(self, module_name: str, signal_name: str):
        """
        Allows modules to register for signals. This tells us what is c
        connected and also allows for early checking of unknown signals
        Modules cannot query signal state of signals they have no registered
        for.
        """
        if signal_name not in signals:
            raise ValueError(f"{signal_name} is not the name of a value signal")

        # Check for duplicates:
        if module_name in self._registered_modules.keys():
            sigs = self._registered_modules[module_name]
            if signal_name in sigs:
                raise ValueError(
                    f"Module {module_name} has already registered for signal {signal_name}"
                )
        else:
            self._registered_modules[module_name] = []
        self._registered_modules[module_name].append(signal_name)
        logger.info("'%s' registered for signal '%s'", module_name, signal_name)

    def getSignalState(self, module_name, signal_name) -> bool:
        """
        Return the state of the named signal to the named module
        """
        if signal_name not in signals:
            raise ValueError(f"{signal_name} is not the name of a signal")

        if module_name not in self._registered_modules.keys():
            raise ValueError(f"{module_name} is not the registered for {signal_name}")

        state = self._signal_state[signal_name]
        logger.debug("'%s' queried signal '%s' -> %s", module_name, signal_name, state)
        return state

    def clock_pulse(self):
        logger.debug("Controller: clock pulse")

    def clock_inv_pulse(self):
        logger.debug("Controller: clock inv pulse")
