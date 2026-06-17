"""
A memory module - allows storage and retrieval of byte values given
an address.

Memory size is specified in *bits* to match the convention used in
hardware devices.

The Memory class is the base for the RAM and ROM classes.

"""

import logging

import numpy as np

from bus import Bus
from controller import Controller
from module import Module
from register import Register
from signals import Signal

logger = logging.getLogger(__name__)


class Memory(Module):
    def __init__(
        self,
        name: str,
        master_bus: Bus,
        in_signal: Signal | None,
        out_signal: Signal | None,
        size: int,
    ):
        super().__init__(name)
        self._master_bus = master_bus
        self._size = size
        self._in_signal = in_signal
        self._out_signal = out_signal
        self._values = np.zeros(size // 8, dtype=np.uint8)
        logger.info("%s: initialised %d bits (%d bytes)", name, size, size // 8)

    def getValue(self, address: int) -> int:
        if address < 0 or address >= len(self._values):
            raise IndexError(
                f"{self._name}: address {address} out of range "
                f"(0-{len(self._values) - 1})"
            )
        value = int(self._values[address]) & 0xFF
        logger.debug("%s: read 0x%02X from address %d", self._name, value, address)
        return value

    def setValue(self, address: int, value: int) -> None:
        if address < 0 or address >= len(self._values):
            raise IndexError(
                f"{self._name}: address {address} out of range "
                f"(0-{len(self._values) - 1})"
            )
        self._values[address] = value & 0xFF
        logger.debug(
            "%s: wrote 0x%02X to address %d", self._name, value & 0xFF, address
        )

    def clear(self) -> None:
        self._values[:] = 0
        logger.debug("%s: cleared", self._name)

    def size(self) -> int:
        return len(self._values)


class RAM(Memory):
    """
    RAM with an associated address register. Bus reads and writes always
    use the address currently held in the memory register.
    Direct getValue/setValue remain available for initialisation and testing.
    """

    def __init__(
        self,
        name: str,
        master_bus: Bus,
        in_signal: Signal,
        out_signal: Signal,
        size: int,
        mem_reg: Register,
        contents_file: str = "",
    ):
        super().__init__(name, master_bus, in_signal, out_signal, size)
        self._mem_reg = mem_reg

        if contents_file:
            raw = np.fromfile(contents_file, dtype=np.uint8)
            if len(raw) > len(self._values):
                raise ValueError(
                    f"File too large for memory ({len(raw)} > {len(self._values)} bytes)"
                )
            self._values[: len(raw)] = raw

    def getState(self) -> dict:
        state = super().getState()
        state["kind"] = "memory"
        state["value"] = self.getValue(self._mem_reg.getValue())
        return state

    def clock_pulse(self) -> None:
        if (
            self._out_signal is not None
            and self._controller
            and self._controller.getSignalState(self._name, self._out_signal)
        ):
            address = self._mem_reg.getValue()
            self._master_bus.setValue(self.getValue(address), self)
            logger.debug(
                "%s: output 0x%02X from address %d to bus",
                self._name, self.getValue(address), address,
            )
        super().clock_pulse()

    def clock_inv_pulse(self) -> None:
        if (
            self._in_signal is not None
            and self._controller
            and self._controller.getSignalState(self._name, self._in_signal)
        ):
            address = self._mem_reg.getValue()
            value = self._master_bus.getValue()
            self.setValue(address, value)
            logger.debug(
                "%s: wrote 0x%02X to address %d from bus", self._name, value, address
            )
        super().clock_inv_pulse()


class ROM(Memory):
    """
    ROM with an associated address register. Bus reads always use the address
    currently held in the memory register. Contents are loaded from a file at
    startup and cannot be written via the bus.
    """

    def __init__(
        self,
        name: str,
        master_bus: Bus,
        out_signal: Signal,
        size: int,
        mem_reg: Register,
        contents_file: str = "",
    ):
        super().__init__(name, master_bus, None, out_signal, size)
        self._mem_reg = mem_reg

        if contents_file:
            raw = np.fromfile(contents_file, dtype=np.uint8)
            if len(raw) > len(self._values):
                raise ValueError(
                    f"File too large for memory ({len(raw)} > {len(self._values)} bytes)"
                )
            self._values[: len(raw)] = raw
            logger.info(
                "%s: loaded %d bytes from '%s' (first bytes: %s)",
                name, len(raw), contents_file,
                " ".join(f"0x{b:02X}" for b in raw[:8]),
            )
        else:
            logger.warning("%s: no file provided — ROM is all zeros", name)

    def getState(self) -> dict:
        state = super().getState()
        state["kind"] = "memory"
        state["value"] = self.getValue(self._mem_reg.getValue())
        return state

    def setValue(self, address: int, value: int) -> None:
        raise TypeError(f"{self._name}: ROM is read-only")

    def clock_pulse(self) -> None:
        if (
            self._out_signal is not None
            and self._controller
            and self._controller.getSignalState(self._name, self._out_signal)
        ):
            address = self._mem_reg.getValue()
            self._master_bus.setValue(self.getValue(address), self)
            logger.debug(
                "%s: output 0x%02X from address %d to bus",
                self._name, self.getValue(address), address,
            )
        super().clock_pulse()
