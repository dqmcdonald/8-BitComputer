"""

A program counter module. Counts up on every clock tick.

Outputs to the master bus when its out_signal is asserted, and can be
loaded from the bus by a JUMP signal.

"""

import logging

from bus import Bus
from controller import Controller
from module import Module
from signals import Signal

logger = logging.getLogger(__name__)


class ProgramCounter(Module):
    def __init__(
        self,
        name: str,
        master_bus: Bus,
        in_signal: Signal,
        out_signal: Signal,
        enable_signal: Signal,
        controller: Controller,
    ) -> None:
        super().__init__(name)
        self._master_bus = master_bus
        self._count = 0
        self._in_signal = in_signal
        self._out_signal = out_signal
        self._enable_signal = enable_signal
        self._controller = controller

    def getCount(self) -> int:
        return self._count

    def reset(self) -> None:
        self._count = 0
        logger.debug("%s: reset to 0", self._name)

    def jumpTo(self, pos: int) -> None:
        self._count = pos & 0xFF
        logger.debug("%s: jumped to %d", self._name, self._count)

    def setupSignals(self, controller: Controller) -> None:
        super().setupSignals(controller)
        controller.registerForSignal(self._name, self._enable_signal)

    def clock_pulse(self) -> None:
        if (
            self._out_signal is not None
            and self._controller
            and self._controller.getSignalState(self._name, self._out_signal)
        ):
            self._master_bus.setValue(self._count, self)
            logger.debug("%s: output %d to bus", self._name, self._count)
        super().clock_pulse()

    def clock_inv_pulse(self) -> None:
        if self._controller and self._controller.getSignalState(
            self._name, self._in_signal
        ):
            self._count = self._master_bus.getValue() & 0xFF
            logger.debug("%s: jumped to %d from bus", self._name, self._count)

        if self._controller and self._controller.getSignalState(
            self._name, self._enable_signal
        ):
            self._count = (self._count + 1) & 0xFF
            logger.debug("%s: count now %d", self._name, self._count)

        super().clock_inv_pulse()
