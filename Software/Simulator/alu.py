"""
The Arithmetic Logic Unit (ALU).

Models the Ben Eater 8-bit ALU: a pair of 74LS283 adders that compute
A + B, or A - B when the subtract control is asserted. Subtraction is done
in two's complement exactly as the hardware does it — each bit of the B
input is XORed with the subtract line (inverting B) and the subtract line
also forces a carry into the low bit, so:

    A + (~B) + 1  ==  A - B

The ALU reads its operands directly from the A and B registers; it is never
loaded from the bus. When its output-enable signal is asserted it drives the
8-bit result onto the bus. It also exposes the carry and zero flags, which a
flags register can latch:

    carry  - the carry-out of the adder. On a subtract, carry == 1 means
             "no borrow" (A >= B), matching the 74LS283 behaviour.
    zero   - set when the 8-bit result is 0x00.
"""

import logging

from bus import Bus
from controller import Controller
from module import Module
from register import Register
from signals import Signal

logger = logging.getLogger(__name__)


class ALU(Module):
    def __init__(
        self,
        name: str,
        master_bus: Bus,
        reg_a: Register,
        reg_b: Register,
        out_signal: Signal,
        sub_signal: Signal,
    ) -> None:
        super().__init__(name)
        self._master_bus = master_bus
        self._reg_a = reg_a
        self._reg_b = reg_b
        self._out_signal = out_signal
        self._sub_signal = sub_signal
        self._cached_carry = False
        self._cached_zero = False

    def setupSignals(self, controller: Controller) -> None:
        # The base class registers the bus output-enable (out_signal). The
        # subtract line is an extra control input with no bus direction, so
        # register it here on top.
        super().setupSignals(controller)
        self._controller = controller
        self._controller.registerForSignal(self._name, self._sub_signal)
        logger.info("%s: registered for subtract signal '%s'", self._name, self._sub_signal.name)

    def _subtracting(self) -> bool:
        return bool(
            self._controller
            and self._controller.getSignalState(self._name, self._sub_signal)
        )

    def _compute(self) -> tuple[int, bool, bool]:
        """
        Combinationally compute (result, carry, zero) from the current A and B
        register values and the subtract line, using two's-complement arithmetic.
        """
        a = self._reg_a.getValue() & 0xFF
        b = self._reg_b.getValue() & 0xFF
        if self._subtracting():
            b_in = b ^ 0xFF  # invert B
            carry_in = 1  # forced carry-in completes the two's complement
        else:
            b_in = b
            carry_in = 0
        raw = a + b_in + carry_in
        result = raw & 0xFF
        carry = bool(raw & 0x100)
        zero = result == 0
        return result, carry, zero

    def getValue(self) -> int:
        """Current 8-bit result (combinational)."""
        result, _, _ = self._compute()
        return result

    def carryFlag(self) -> bool:
        return self._cached_carry

    def zeroFlag(self) -> bool:
        return self._cached_zero

    def getState(self) -> dict:
        state = super().getState()
        state["value"] = self.getValue()
        state["kind"] = "alu"
        return state

    def clock_pulse(self) -> None:
        result, carry, zero = self._compute()
        self._cached_carry = carry
        self._cached_zero = zero
        if self._controller and self._controller.getSignalState(
            self.getName(), self._out_signal
        ):
            self._master_bus.setValue(result, self)
            logger.debug(
                "%s: output 0x%02X to bus (carry=%d zero=%d)",
                self._name,
                result,
                carry,
                zero,
            )
        super().clock_pulse()
