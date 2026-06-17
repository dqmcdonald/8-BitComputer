"""

A class with models an 8-Bit bus. Various instances of this may
be created during the simulator but there's also one master bus that can
be imported as 'master' from this module

"""

import logging

from module import Module

logger = logging.getLogger(__name__)


class Bus(Module):
    def __init__(self, name: str = "Bus") -> None:
        super().__init__(name)
        self._value = 0
        self._driver: Module | None = None

    def setValue(self, value: int, module: Module) -> None:
        if not 0 <= value <= 255:
            raise ValueError(f"Bus value {value} out of range 0-255")
        if self._driver is not None:
            logger.warning("%s: contention — %s tried to set bus already driven by %s",
                           self._name, module.getName(), self._driver.getName())
            raise ValueError(f"Bus already set by {self._driver.getName()}")
        self._value = value
        self._driver = module
        logger.debug("%s: set to 0x%02X by %s", self._name, value, module.getName())

    def getValue(self) -> int:
        return self._value

    def getBit(self, n: int) -> int:
        return (self._value >> n) & 1

    def clock_pulse(self) -> None:
        logger.debug("%s: released (clock pulse), was 0x%02X", self._name, self._value)
        self._driver = None
        super().clock_pulse()

    def setBits(self, bits: tuple[int, ...], module: Module) -> None:
        if self._driver is not None:
            logger.warning("%s: contention — %s tried to set bus already driven by %s",
                           self._name, module.getName(), self._driver.getName())
            raise ValueError(f"Bus already set by {self._driver.getName()}")
        if len(bits) != 8 or not all(b in (0, 1) for b in bits):
            raise ValueError("bits must be a tuple of exactly 8 ints, each 0 or 1")
        self._value = sum(b << (7 - n) for n, b in enumerate(bits))
        self._driver = module
        logger.debug("%s: set to 0x%02X by %s", self._name, self._value, module.getName())

    def getBits(self) -> tuple[int, ...]:
        return tuple((self._value >> n) & 1 for n in range(7, -1, -1))

    def getDriver(self) -> Module | None:
        return self._driver

    def clear(self) -> None:
        logger.debug("%s: cleared", self._name)
        self._value = 0
        self._driver = None

    def getState(self) -> dict:
        driver = self._driver
        return {
            "name": self._name,
            "value": self._value,
            "driver": driver.getName() if driver is not None else None,
            "signals": {},
        }
