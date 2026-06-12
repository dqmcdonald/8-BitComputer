# The Basic class for the modules. Provides all the very lowest level services such as responding to the clock tick.

import logging

from controller import Controller

logger = logging.getLogger(__name__)


class Module:
    def __init__(self, name: str):
        self._name = name

    def getName(self) -> str:
        return self._name

    def clock_pulse(self) -> None:
        logger.debug("%s: clock pulse", self._name)

    def clock_inv_pulse(self) -> None:
        logger.debug("%s: clock inv pulse", self._name)

    def setupSignals(self, controller: Controller) -> None:
        pass
