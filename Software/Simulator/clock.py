"""
Clock class for 8-Bit Computer Simulator

"""

import logging
import time
from enum import IntEnum, auto
from itertools import chain
from signal import SIGABRT

from bus import Bus
from controller import Controller
from module import Module
from signals import Signal

logger = logging.getLogger(__name__)


class ClockMode(IntEnum):
    SINGLE_STEP = auto()  # One step at a time
    CONTINUOUS = auto()  # Run con


class Clock:
    def __init__(self):
        self._modules = []
        self._buses = []
        self._clock_mode: ClockMode = ClockMode.CONTINUOUS
        self._clock_speed = 1  # Clock speed in HZ
        self._controller: Controller | None = None
        self._tick_count = 0

    def addModule(self, mod: Module):
        if mod in self._modules:
            logger.warning(
                "Module '%s' is already registered with the clock", mod.getName()
            )
            raise ValueError(
                f"Module '{mod.getName()}' is already registered with the clock"
            )
        self._modules.append(mod)
        logger.info("Module '%s' registered with clock", mod.getName())

    def setupSignals(self, controller: Controller) -> None:
        self._controller = controller
        self._controller.registerForSignal("Clock", Signal.HALT)
        self._controller.registerForSignal("Clock", Signal.CLEA)
        logger.info("Clock signals registered")

    def addBus(self, bus: Bus):
        if bus in self._buses:
            logger.warning(
                "Bus '%s' is already registered with the clock", bus.getName()
            )
            raise ValueError(
                f"Bus '{bus.getName()}' is already registered with the clock"
            )
        self._buses.append(bus)
        logger.info("Bus '%s' registered with clock", bus.getName())

    def addController(self, controller: Controller):
        self._controller = controller
        logger.info("Controller registered with clock")

    def setSpeed(self, speed: float) -> None:
        self._clock_speed = speed
        logger.info("Clock speed set to %gHz", speed)

    def setSingleStepMode(self) -> None:
        self._clock_mode = ClockMode.SINGLE_STEP
        logger.info("Clock mode: SINGLE_STEP")

    def setContinuousMode(self) -> None:
        self._clock_mode = ClockMode.CONTINUOUS
        logger.info("Clock mode: CONTINUOUS")

    def tick(self):
        self._tick_count += 1
        logger.debug("--- tick %d ---", self._tick_count)
        self._controller.clock_pulse()
        for m in chain(self._buses, self._modules):
            m.clock_pulse()
        logger.debug("--- inv tick %d ---", self._tick_count)
        self._controller.clock_inv_pulse()
        for m in chain(self._buses, self._modules):
            m.clock_inv_pulse()

    def run(self):
        """
        Will run the clock depending on the current mode. If single
        step then do one tick and return. If in run mode, run continuously
        until a HLT condition with a delay to achieve the required speed.
        """
        logger.info(
            "Clock run: mode=%s speed=%gHz", self._clock_mode.name, self._clock_speed
        )
        if self._clock_mode == ClockMode.SINGLE_STEP:
            self.tick()
        else:
            do_run = True
            while do_run:
                self.tick()
                time.sleep(1.0 / self._clock_speed)
                if self._controller.getSignalState("Clock", Signal.HALT):
                    do_run = False
