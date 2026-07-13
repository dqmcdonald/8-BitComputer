"""
The main simulator class

"""

import argparse
import logging

from alu import ALU
from bus import Bus
from clock import Clock, ClockMode
from controller import Controller
from flags import FlagsRegister
from memory import RAM, ROM
from progcounter import ProgramCounter
from register import OutputRegister, Register
from signals import Signal

logger = logging.getLogger(__name__)

K = 1024


class Simulator:
    def __init__(
        self,
        ram_file: str = "",
        prog_rom_file: str = "",
        rom1_file: str = "rom1.bin",
        rom2_file: str = "rom2.bin",
    ) -> None:
        self._modules = []
        self.constructSimulator(ram_file, prog_rom_file, rom1_file, rom2_file)
        self.setupClock()
        self.setupSignals()

    def constructSimulator(
        self,
        ram_file: str = "",
        prog_rom_file: str = "",
        rom1_file: str = "rom1.bin",
        rom2_file: str = "rom2.bin",
    ) -> None:
        """
        Instantiate all the objects for the simulator
        """
        logger.info("Constructing simulator")
        self._controller = Controller(256 * K, 256 * K, rom1_file, rom2_file)
        self._clock = Clock()
        self._master_bus = Bus("Master Bus")

        # Build registers
        self._registerA = Register(
            "RegisterA", self._master_bus, Signal.ARGI, Signal.ARGO
        )
        self._modules.append(self._registerA)
        self._registerB = Register(
            "RegisterB", self._master_bus, Signal.BRGI, Signal.BRGO
        )
        self._modules.append(self._registerB)

        # The ALU reads A and B directly and drives the bus on ALUO.
        self._alu = ALU(
            "ALU",
            self._master_bus,
            self._registerA,
            self._registerB,
            Signal.ALUO,
            Signal.SUBT,
        )
        self._modules.append(self._alu)

        # The flags register latches the ALU's carry/zero on FLGI; it feeds
        # the control unit rather than the bus.
        self._flags = FlagsRegister("Flags", self._alu, Signal.FLGI)
        self._modules.append(self._flags)

        self._instructionReg = Register(
            "InstructionReg", self._master_bus, Signal.IRGI, Signal.IRGO
        )
        self._modules.append(self._instructionReg)

        self._memory_add_reg = Register(
            "MemoryAddressReg", self._master_bus, Signal.MRAI, None
        )
        self._modules.append(self._memory_add_reg)

        self._outputReg = OutputRegister(
            "Output Register", self._master_bus, Signal.OUTI, None
        )
        self._modules.append(self._outputReg)

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

        self._prog_rom_reg = Register(
            "ProgROMReg", self._master_bus, Signal.MROI, None
        )
        self._modules.append(self._prog_rom_reg)

        self._prog_rom = ROM(
            "ProgROM",
            self._master_bus,
            Signal.ROMO,
            64 * K,
            self._prog_rom_reg,
            prog_rom_file,
        )
        self._modules.append(self._prog_rom)

        self._prog_counter = ProgramCounter(
            "ProgCounter",
            self._master_bus,
            Signal.JUMP,
            Signal.COUO,
            Signal.COUE,
            self._controller,
        )
        self._modules.append(self._prog_counter)

        self._controller.setInstructionSource(
            lambda: self._instructionReg.getValue()
        )
        self._controller.setFlagsSource(
            lambda: self._flags.getFlags()
        )

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

    def getModules(self) -> list:
        return list(self._modules)

    def getBus(self) -> "Bus":
        return self._master_bus

    def getClock(self) -> "Clock":
        return self._clock

    def getController(self) -> "Controller":
        return self._controller

    def getProgramBytes(self, n: int = 256) -> list[int]:
        """Return the first n bytes of the program ROM."""
        return [int(self._prog_rom.getValue(i)) for i in range(min(n, self._prog_rom.size()))]

    def getProgramCounter(self) -> int:
        return self._prog_counter.getCount()

    def reset(self) -> None:
        self._clock.reset()
        self._master_bus.clear()
        self._controller.reset()
        for m in self._modules:
            m.reset()
        logger.info("Simulator reset")

    def run(self) -> None:
        logger.info("Simulator running")
        if self._clock.getMode() == ClockMode.SINGLE_STEP:
            while True:
                self._clock.tick()
                if self._controller.getSignalState("Clock", Signal.HALT):
                    logger.info("Simulator halted (HALT signal)")
                    break
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
        "prog_rom",
        metavar="PROG_ROM",
        help="Binary file to load into program ROM",
    )
    parser.add_argument(
        "--ram",
        "-r",
        default="",
        metavar="FILE",
        help="Binary file to load into RAM at startup",
    )
    parser.add_argument(
        "--rom1",
        default="rom1.bin",
        metavar="FILE",
        help="Microcode ROM 1 file (default: rom1.bin)",
    )
    parser.add_argument(
        "--rom2",
        default="rom2.bin",
        metavar="FILE",
        help="Microcode ROM 2 file (default: rom2.bin)",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable DEBUG-level logging for all modules",
    )
    parser.add_argument(
        "--debug-module",
        "-D",
        action="append",
        metavar="MODULE",
        default=[],
        help=(
            "Enable DEBUG logging for a specific module "
            "(e.g. -D controller -D memory). "
            "Valid names: alu, bus, clock, controller, flags, memory, "
            "module, progcounter, register, simulator. "
            "Can be given multiple times."
        ),
    )
    parser.add_argument(
        "--gui",
        "-g",
        action="store_true",
        help="Launch the graphical user interface",
    )
    args = parser.parse_args()

    import os
    errors = []
    for flag, path in [
        ("prog_rom",   args.prog_rom),
        ("--ram",      args.ram),
        ("--rom1",     args.rom1),
        ("--rom2",     args.rom2),
    ]:
        if path and not os.path.exists(path):
            errors.append(f"  {flag}: '{path}' not found")
    if errors:
        parser.error("File(s) not found:\n" + "\n".join(errors))

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    for module_name in args.debug_module:
        logging.getLogger(module_name).setLevel(logging.DEBUG)

    sim = Simulator(
        ram_file=args.ram,
        prog_rom_file=args.prog_rom,
        rom1_file=args.rom1,
        rom2_file=args.rom2,
    )

    if args.gui:
        import tkinter as tk
        from gui.app import SimulatorGUI
        root = tk.Tk()
        root.geometry("900x640")
        SimulatorGUI(root, sim)
        root.mainloop()
    else:
        clock_mode = (
            ClockMode.SINGLE_STEP if args.mode == "single" else ClockMode.CONTINUOUS
        )
        sim.setClockProps(args.speed, clock_mode)
        sim.run()
