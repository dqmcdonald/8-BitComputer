"""
The main simulator class

"""

import logging
from queue import SimpleQueue

from alu import ALU
from bus import Bus
from clock import Clock, ClockMode
from controller import Controller
from memory import Memory
from module import Module
from register import Register

logger = logging.getLogger(__name__)


class Simulator:
    def __init__(self) -> None:
        self._modules = []
        self.constructSimulator()
        self.setupClock()
        self.setupSignals()

    def constructSimulator(self) -> None:
        """
        Instantiate all the objects for the simulator
        """
        logger.info("Constructing simulator")
        self._controller = Controller()
        self._clock = Clock()
        self._master_bus = Bus("Master Bus")

        # Build registers
        self._registerA = Register("RegisterA", self._master_bus, "RAIN", "RAOU")
        self._modules.append(self._registerA)
        self._registerB = Register("RegisterB", self._master_bus, "RBIN", "RBOU")
        self._modules.append(self._registerB)

        # The ALU reads A and B directly and drives the bus on ALUO.
        self._alu = ALU(
            "ALU", self._master_bus, self._registerA, self._registerB, "ALUO", "SUBT"
        )
        self._modules.append(self._alu)

        self._instructionReg = Register(
            "InstructionReg", self._master_bus, "IRIN", "IROU"
        )
        self._modules.append(self._instructionReg)

        self._ram = Memory("RAM", self._master_bus, "RAMI", "RAMO", 1024)
        self._modules.append(self._ram)

    def setupClock(self) -> None:
        self._clock.addBus(self._master_bus)
        self._clock.addController(self._controller)

    def setupSignals(self) -> None:
        """
        Make all signal connections
        """
        self._clock.setupSignals(self._controller)
        for m in self._modules:
            m.setupSignals(self._controller)

    def setClockProps(
        self, speed: float, clock_mode: ClockMode = ClockMode.CONTINUOUS
    ) -> None:
        """ """
        if clock_mode == ClockMode.CONTINUOUS:
            self._clock.setContinuousMode()
        elif clock_mode == ClockMode.SINGLE_STEP:
            self._clock.setSingleStepMode()

        self._clock.setSpeed(speed)

    def run(self) -> None:
        logger.info("Simulator running")
        if self._clock._clock_mode == ClockMode.SINGLE_STEP:
            while True:
                self._clock.tick()
                response = input("\nEnter to step, 'q' to quit: ").strip().lower()
                if response == "q":
                    logger.info("Simulator stopped by user")
                    break
        else:
            self._clock.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s %(name)s: %(message)s",
    )
    sim = Simulator()
    sim.setClockProps(0.2, ClockMode.SINGLE_STEP)
    sim.run()
