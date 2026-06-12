# The Basic class for the modules. Provides all the very lowest level services such as responding to the clock tick.

import logging

from controller import Controller

logger = logging.getLogger(__name__)


class Module:
    def __init__(self, name: str):
        self._name = name
        self._in_signal: str = ""
        self._out_signal: str = ""
        self._controller: Controller | None = None

    def getName(self) -> str:
        return self._name

    def clock_pulse(self) -> None:
        logger.debug("%s: clock pulse", self._name)

    def clock_inv_pulse(self) -> None:
        logger.debug("%s: clock inv pulse", self._name)

    def setupSignals(self, controller: Controller) -> None:
        self._controller = controller
        if self._in_signal:
            self._controller.registerForSignal(self._name, self._in_signal)
        if self._out_signal:
            self._controller.registerForSignal(self._name, self._out_signal)
        if self._in_signal or self._out_signal:
            logger.info("%s: registered for signals '%s' (in) and '%s' (out)",
                        self._name, self._in_signal, self._out_signal)
