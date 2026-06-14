"""
The main simulator class

"""

import argparse
import logging
from queue import SimpleQueue

from alu import ALU
from bus import Bus
from clock import Clock, ClockMode
from controller import Controller
from flags import FlagsRegister
from memory import RAM
from progcounter import ProgramCounter
from register import Register
from signals import Signal

logger = logging.getLogger(__name__)


class Simulator:
    def __init__(self, ram_file: str = "") -> None:
        self._modules = []
        self.constructSimulator(ram_file)
        self.setupClock()
        self.setupSignals()

    def constructSimulator(self, ram_file: str = "") -> None:
        """
        Instantiate all the objects for the simulator
        """
        logger.info("Constructing simulator")
        self._controller = Controller()
        self._clock = Clock()
        self._master_bus = Bus("Master Bus")

        # Build registers
        self._registerA = Register("RegisterA", self._master_bus, Signal.RAIN, Signal.RAOU)
        self._modules.append(self._registerA)
        self._registerB = Register("RegisterB", self._master_bus, Signal.RBIN, Signal.RBOU)
        self._modules.append(self._registerB)

        # The ALU reads A and B directly and drives the bus on ALUO.
        self._alu = ALU(
            "ALU", self._master_bus, self._registerA, self._registerB, Signal.ALUO, Signal.SUBT
        )
        self._modules.append(self._alu)

        # The flags register latches the ALU's carry/zero on FLGI; it feeds
        # the control unit rather than the bus.
        self._flags = FlagsRegister("Flags", self._alu, Signal.FLGI)
        self._modules.append(self._flags)

        self._instructionReg = Register(
            "InstructionReg", self._master_bus, Signal.IRIN, Signal.IROU
        )
        self._modules.append(self._instructionReg)

        self._memory_add_reg = Register(
            "MemoryAddressReg", self._master_bus, Signal.MIIN, Signal.MIOU
        )
        self._modules.append(self._memory_add_reg)

        self._ram = RAM(
            "RAM",
            self._master_bus,
            Signal.RAMI,
            Signal.RAMO,
            1024,
            self._memory_add_reg,
            ram_file,
        )
        self._modules.append(self._ram)

        self._prog_counter = ProgramCounter("ProgCounter", self._master_bus, Signal.JUMP, Signal.PCOU)
        self._modules.append(self._prog_counter)

    def setupClock(self) -> None:
        self._clock.addBus(self._master_bus)
        self._clock.addController(self._controller)
        for m in self._modules:
            self._clock.addModule(m)

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
    parser = argparse.ArgumentParser(description="8-Bit Computer Simulator")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["single", "continuous"],
        default="continuous",
        help="Clock mode: 'single' for single-step, 'continuous' to run freely (default: continuous)",
    )
    parser.add_argument(
        "--speed",
        "-s",
        type=float,
        default=1.0,
        help="Clock speed in Hz (default: 1.0)",
    )
    parser.add_argument(
        "--ram",
        "-r",
        default="",
        metavar="FILE",
        help="Binary file to load into RAM at startup",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable DEBUG-level logging (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    clock_mode = (
        ClockMode.SINGLE_STEP if args.mode == "single" else ClockMode.CONTINUOUS
    )

    sim = Simulator(ram_file=args.ram)
    sim.setClockProps(args.speed, clock_mode)
    sim.run()
