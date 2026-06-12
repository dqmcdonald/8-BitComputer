"""
Registers store 8-bit values. They can read from and write to the bus.
The arthmetic logic unit can access them to perform arithmatic.

"""

import logging

from bus import Bus
from controller import Controller
from module import Module

logger = logging.getLogger(__name__)


class Register(Module):
    def __init__(
        self,
        name: str,
        master_bus: Bus,
        in_signal: str,
        out_signal: str,
    ) -> None:
        super().__init__(name)
        self._value = 0
        self._master_bus = master_bus
        self._controller: Controller | None = None
        self._in_signal = in_signal
        self._out_signal = out_signal

    def getValue(self) -> int:
        return self._value & 0xFF

    def setValue(self, value: int) -> None:
        self._value = value & 0xFF
        logger.debug("%s: value set to 0x%02X", self._name, self._value)

    def setupSignals(self, controller: Controller) -> None:
        self._controller = controller
        self._controller.registerForSignal(self.getName(), self._in_signal)
        self._controller.registerForSignal(self.getName(), self._out_signal)
        logger.info(
            "%s: registered for signals '%s' (in) and '%s' (out)",
            self._name,
            self._in_signal,
            self._out_signal,
        )

    def clock_pulse(self) -> None:
        if self._controller and self._controller.getSignalState(
            self.getName(), self._out_signal
        ):
            self._master_bus.setValue(self._value, self)
            logger.debug("%s: output 0x%02X to bus", self._name, self._value)
        super().clock_pulse()

    def clock_inv_pulse(self) -> None:
        if self._controller and self._controller.getSignalState(
            self.getName(), self._in_signal
        ):
            self._value = self._master_bus.getValue()
            logger.debug("%s: latched 0x%02X from bus", self._name, self._value)
        super().clock_inv_pulse()
