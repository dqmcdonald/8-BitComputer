"""
The main routine


"""

from bus import master as masterbus
from clock import clock as clk
from control import control_mod
from module import Module

mod = Module("Test Mod")

if __name__ == "__main__":
    print(masterbus.getValue())
    masterbus.setValue(0b10001001, mod)
    print(masterbus.getValue())
    print(masterbus.getBits())
    clk.addBus(masterbus)
    clk.addModule(mod)

    for i in range(10):
        clk.tick()
        masterbus.setValue(0b10001001 + i, mod)
        print(masterbus.getBits())

    control_mod.registerForSignal(mod.getName(), "HALT")
    print(control_mod.getSignalState(mod.getName(), "HALT"))

    print("Single Step Mode")
    clk.setSingleStepMode()
    clk.run()
    print("Continuous Mode at 2Hz")
    clk.setContinuousMode()
    clk.setSpeed(2.0)
