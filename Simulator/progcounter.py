"""

A program counter module. Counts up on every clock tick.

Outputs to the master bus on PCOU and can be loaded from
the bus by a JUMP signal.

"""

import logging

from bus import Bus
from module import Module

logger = logging.getLogger(__name__)


class ProgramCounter(Module):
    def __init__(self, name: str, master_bus: Bus, in_signal: str, out_signal: str) -> None:
        super().__init__(name)
        self._master_bus = master_bus
        self._count = 0
        self._in_signal = in_signal
        self._out_signal = out_signal

    def getCount(self) -> int:
        return self._count

    def reset(self) -> None:
        self._count = 0
        logger.debug("%s: reset to 0", self._name)

    def jumpTo(self, pos: int) -> None:
        self._count = pos & 0xFF
        logger.debug("%s: jumped to %d", self._name, self._count)

    def clock_pulse(self) -> None:
        if self._controller and self._controller.getSignalState(self._name, self._out_signal):
            self._master_bus.setValue(self._count, self)
            logger.debug("%s: output %d to bus", self._name, self._count)
        self._count = (self._count + 1) & 0xFF
        logger.debug("%s: count now %d", self._name, self._count)
        super().clock_pulse()

    def clock_inv_pulse(self) -> None:
        if self._controller and self._controller.getSignalState(self._name, self._in_signal):
            self._count = self._master_bus.getValue() & 0xFF
            logger.debug("%s: jumped to %d from bus", self._name, self._count)
        super().clock_inv_pulse()
