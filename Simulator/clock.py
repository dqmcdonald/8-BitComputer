"""
Clock class for 8-Bit Computer Simulator

"""

import time
from enum import IntEnum, auto
from itertools import chain

from bus import Bus
from control import control_mod
from module import Module


class ClockMode(IntEnum):
    SINGLE_STEP = auto()  # One step at a time
    CONTINUOUS = auto()  # Run con


class Clock:
    def __init__(self):
        self._modules = []
        self._buses = []
        self._clock_mode: ClockMode = ClockMode.CONTINUOUS
        self._clock_speed = 1  # Clock speed in HZ

    def addModule(self, mod: Module):
        if mod in self._modules:
            print(f"Error - module {mod.getName()} is already registered")
            raise ValueError
        self._modules.append(mod)

    def addBus(self, bus: Bus):
        if bus in self._buses:
            print(f"Error - bus {bus.getName()} is already registered")
            raise ValueError
        self._buses.append(bus)

    def setSpeed(self, speed: float) -> None:
        self._clock_speed = speed

    def setSingleStepMode(self) -> None:
        self._clock_mode = ClockMode.SINGLE_STEP

    def setContinuousMode(self) -> None:
        self._clock_mode = ClockMode.CONTINUOUS

    def tick(self):
        # Send a single pulse to every registered bus and module
        # Send to control module first:
        control_mod.clock_pulse()
        for m in chain(self._buses, self._modules):
            m.clock_pulse()
            print("pulse")
        control_mod.clock_inv_pulse()
        for m in chain(self._buses, self._modules):
            m.clock_inv_pulse()
            print("inv_pulse")

    def run(self):
        """
        Will run the clock depending on the current mode. If single
        step then do one tick and return. If in run mode, run continuously
        until a HLT condition with a delay to achieve the required speed.
        """
        if self._clock_mode == ClockMode.SINGLE_STEP:
            self.tick()
        else:
            do_run = True
            while do_run:
                self.tick()
                time.sleep(1.0 / self._clock_speed)
                # TODO: add stopping condition here - checking for
                # HLT


# Single shared Clock instance — import this rather than constructing Clock()
clock = Clock()
