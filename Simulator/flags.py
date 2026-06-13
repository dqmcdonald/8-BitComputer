"""
The Flags Register.

Latches the ALU's carry and zero flags when its load signal (FLGI) is
asserted, on the latch phase of the clock — the same phase a register uses
to capture from the bus. The stored flags feed the control unit's microcode
address so that conditional instructions (e.g. jump-if-carry, jump-if-zero)
can branch on the result of the previous ALU operation.

Unlike a data register the flags register never drives the bus; it reads the
ALU directly and presents its two bits to the control logic.
"""

import logging

from alu import ALU
from controller import Controller
from module import Module

logger = logging.getLogger(__name__)


class FlagsRegister(Module):
    def __init__(self, name: str, alu: ALU, in_signal: str) -> None:
        super().__init__(name)
        self._alu = alu
        self._in_signal = in_signal
        self._carry = False
        self._zero = False

    def getCarry(self) -> bool:
        return self._carry

    def getZero(self) -> bool:
        return self._zero

    def clear(self) -> None:
        self._carry = False
        self._zero = False
        logger.debug("%s: cleared", self._name)

    def clock_inv_pulse(self) -> None:
        if self._controller and self._controller.getSignalState(
            self.getName(), self._in_signal
        ):
            self._carry = self._alu.carryFlag()
            self._zero = self._alu.zeroFlag()
            logger.debug(
                "%s: latched carry=%d zero=%d", self._name, self._carry, self._zero
            )
        super().clock_inv_pulse()
