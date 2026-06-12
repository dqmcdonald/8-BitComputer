"""
A memory module - allows storage and retrieval of byte values given
an address.

Memory size is specified in *bits* to match the convention used in
hardware devices.

This can be substantiated directly to be a RAM type mechanism and
subclassed to make a ROM.
"""

import logging

import numpy as np

from bus import Bus
from controller import Controller
from module import Module

logger = logging.getLogger(__name__)


class Memory(Module):
    def __init__(
        self, name: str, master_bus: Bus, in_signal: str, out_signal: str, size: int
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
        logger.debug("%s: wrote 0x%02X to address %d", self._name, value & 0xFF, address)

    def clear(self) -> None:
        self._values[:] = 0
        logger.debug("%s: cleared", self._name)

    def size(self) -> int:
        return len(self._values)
