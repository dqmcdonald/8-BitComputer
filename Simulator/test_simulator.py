"""
PyTest suite for the 8-Bit Computer Simulator classes.
"""

from unittest.mock import patch

import pytest

from alu import ALU
from bus import Bus
from clock import Clock, ClockMode
from controller import Controller, signals
from flags import FlagsRegister
from module import Module
from memory import Memory, RAM
from progcounter import ProgramCounter
from register import Register

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class RecordingModule(Module):
    """Module subclass that records clock calls."""

    def __init__(self, name: str):
        super().__init__(name)
        self.pulse_count = 0
        self.inv_pulse_count = 0

    def clock_pulse(self) -> None:
        self.pulse_count += 1

    def clock_inv_pulse(self) -> None:
        self.inv_pulse_count += 1


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class TestModule:
    def test_name(self):
        m = Module("ALU")
        assert m.getName() == "ALU"

    def test_clock_pulse_does_not_raise(self):
        Module("x").clock_pulse()

    def test_clock_inv_pulse_does_not_raise(self):
        Module("x").clock_inv_pulse()


# ---------------------------------------------------------------------------
# Bus
# ---------------------------------------------------------------------------


class TestBus:
    @pytest.fixture
    def bus(self):
        return Bus()

    @pytest.fixture
    def mod(self):
        return Module("Driver")

    def test_initial_value_is_zero(self, bus):
        assert bus.getValue() == 0

    def test_initial_driver_is_none(self, bus):
        assert bus.getDriver() is None

    def test_set_get_value(self, bus, mod):
        bus.setValue(42, mod)
        assert bus.getValue() == 42

    def test_set_records_driver(self, bus, mod):
        bus.setValue(10, mod)
        assert bus.getDriver() is mod

    def test_value_too_high_raises(self, bus, mod):
        with pytest.raises(ValueError):
            bus.setValue(256, mod)

    def test_value_negative_raises(self, bus, mod):
        with pytest.raises(ValueError):
            bus.setValue(-1, mod)

    def test_contention_raises(self, bus):
        m1 = Module("M1")
        m2 = Module("M2")
        bus.setValue(1, m1)
        with pytest.raises(ValueError):
            bus.setValue(2, m2)

    def test_clear_resets_value_and_driver(self, bus, mod):
        bus.setValue(0xFF, mod)
        bus.clear()
        assert bus.getValue() == 0
        assert bus.getDriver() is None

    def test_clear_allows_new_driver(self, bus):
        m1 = Module("M1")
        m2 = Module("M2")
        bus.setValue(1, m1)
        bus.clear()
        bus.setValue(2, m2)
        assert bus.getDriver() is m2

    def test_get_bit(self, bus, mod):
        bus.setValue(0b10001001, mod)
        assert bus.getBit(7) == 1
        assert bus.getBit(6) == 0
        assert bus.getBit(3) == 1
        assert bus.getBit(0) == 1

    def test_get_bits_msb_first(self, bus, mod):
        bus.setValue(0b10001001, mod)
        assert bus.getBits() == (1, 0, 0, 0, 1, 0, 0, 1)

    def test_set_bits_round_trip(self, bus, mod):
        bits = (1, 0, 1, 1, 0, 0, 1, 0)
        bus.setBits(bits, mod)
        assert bus.getBits() == bits

    def test_set_bits_wrong_length_raises(self, bus, mod):
        with pytest.raises(ValueError):
            bus.setBits((1, 0, 1), mod)

    def test_set_bits_invalid_value_raises(self, bus, mod):
        with pytest.raises(ValueError):
            bus.setBits((1, 0, 1, 0, 1, 0, 1, 2), mod)

    def test_set_bits_contention_raises(self, bus):
        m1 = Module("M1")
        m2 = Module("M2")
        bus.setBits((1, 0, 0, 0, 0, 0, 0, 1), m1)
        with pytest.raises(ValueError):
            bus.setBits((0, 0, 0, 0, 0, 0, 0, 1), m2)

    def test_clock_pulse_clears_driver(self, bus, mod):
        bus.setValue(0xAB, mod)
        bus.clock_pulse()
        assert bus.getDriver() is None

    def test_clock_pulse_preserves_value(self, bus, mod):
        bus.setValue(0xAB, mod)
        bus.clock_pulse()
        assert bus.getValue() == 0xAB


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------


class TestClock:
    @pytest.fixture
    def clk(self):
        return Clock()

    @pytest.fixture
    def ctrl(self):
        return Controller()

    def test_add_module(self, clk):
        m = Module("M")
        clk.addModule(m)
        assert m in clk._modules

    def test_add_duplicate_module_raises(self, clk):
        m = Module("M")
        clk.addModule(m)
        with pytest.raises(ValueError):
            clk.addModule(m)

    def test_add_bus(self, clk):
        b = Bus()
        clk.addBus(b)
        assert b in clk._buses

    def test_add_duplicate_bus_raises(self, clk):
        b = Bus()
        clk.addBus(b)
        with pytest.raises(ValueError):
            clk.addBus(b)

    def test_setup_signals_registers_clock(self, clk, ctrl):
        clk.setupSignals(ctrl)
        assert "HALT" in ctrl._registered_modules["Clock"]
        assert "CLEA" in ctrl._registered_modules["Clock"]

    def test_add_controller(self, clk, ctrl):
        clk.addController(ctrl)
        assert clk._controller is ctrl

    def test_tick_calls_pulse_and_inv_pulse(self, clk, ctrl):
        clk.setupSignals(ctrl)
        m = RecordingModule("M")
        clk.addModule(m)
        clk.tick()
        assert m.pulse_count == 1
        assert m.inv_pulse_count == 1

    def test_tick_calls_controller_first(self, clk):
        call_order = []

        class TrackedController(Controller):
            def clock_pulse(self):
                call_order.append("ctrl_pulse")
            def clock_inv_pulse(self):
                call_order.append("ctrl_inv")

        class TrackedModule(Module):
            def clock_pulse(self):
                call_order.append("module_pulse")
            def clock_inv_pulse(self):
                call_order.append("module_inv")

        clk.addController(TrackedController())
        clk.addModule(TrackedModule("M"))
        clk.tick()
        assert call_order == ["ctrl_pulse", "module_pulse", "ctrl_inv", "module_inv"]

    def test_tick_calls_buses_before_modules(self, clk, ctrl):
        call_order = []
        clk.addController(ctrl)

        class TrackedBus(Bus):
            def clock_pulse(self):
                call_order.append("bus_pulse")
                super().clock_pulse()
            def clock_inv_pulse(self):
                call_order.append("bus_inv")

        class TrackedModule(Module):
            def clock_pulse(self):
                call_order.append("module_pulse")
            def clock_inv_pulse(self):
                call_order.append("module_inv")

        clk.addBus(TrackedBus())
        clk.addModule(TrackedModule("M"))
        clk.tick()
        assert call_order == ["bus_pulse", "module_pulse", "bus_inv", "module_inv"]

    def test_default_mode_is_continuous(self, clk):
        assert clk._clock_mode == ClockMode.CONTINUOUS

    def test_set_single_step_mode(self, clk):
        clk.setSingleStepMode()
        assert clk._clock_mode == ClockMode.SINGLE_STEP

    def test_set_continuous_mode(self, clk):
        clk.setSingleStepMode()
        clk.setContinuousMode()
        assert clk._clock_mode == ClockMode.CONTINUOUS

    def test_set_speed(self, clk):
        clk.setSpeed(4.0)
        assert clk._clock_speed == 4.0

    def test_run_single_step_ticks_once(self, clk, ctrl):
        clk.setupSignals(ctrl)
        m = RecordingModule("M")
        clk.addModule(m)
        clk.setSingleStepMode()
        clk.run()
        assert m.pulse_count == 1
        assert m.inv_pulse_count == 1

    def test_run_continuous_sleeps_at_correct_rate(self, clk, ctrl):
        clk.setupSignals(ctrl)
        m = RecordingModule("M")
        clk.addModule(m)
        clk.setContinuousMode()
        clk.setSpeed(2.0)
        tick_limit = 3
        with patch("clock.time.sleep") as mock_sleep:
            original_tick = clk.tick
            call_count = 0

            def limited_tick():
                nonlocal call_count
                original_tick()
                call_count += 1
                if call_count >= tick_limit:
                    raise StopIteration

            clk.tick = limited_tick
            with pytest.raises(StopIteration):
                clk.run()
        mock_sleep.assert_called_with(0.5)  # 1.0 / 2Hz
        assert m.pulse_count == tick_limit


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class TestController:
    @pytest.fixture
    def ctrl(self):
        return Controller()

    def test_all_signals_start_false(self, ctrl):
        for sig in signals:
            assert ctrl._signal_state[sig] is False

    def test_all_known_signals_present(self, ctrl):
        assert set(ctrl._signal_state.keys()) == signals

    def test_clear_resets_signals_to_false(self, ctrl):
        for sig in signals:
            ctrl._signal_state[sig] = True
        ctrl.clear()
        assert all(v is False for v in ctrl._signal_state.values())

    def test_register_for_valid_signal(self, ctrl):
        sig = next(iter(signals))
        ctrl.registerForSignal("ALU", sig)
        assert sig in ctrl._registered_modules["ALU"]

    def test_register_for_unknown_signal_raises(self, ctrl):
        with pytest.raises(ValueError):
            ctrl.registerForSignal("ALU", "UNKNOWN_SIGNAL")

    def test_register_duplicate_raises(self, ctrl):
        sig = next(iter(signals))
        ctrl.registerForSignal("ALU", sig)
        with pytest.raises(ValueError):
            ctrl.registerForSignal("ALU", sig)

    def test_register_multiple_signals_for_same_module(self, ctrl):
        for sig in signals:
            ctrl.registerForSignal("ALU", sig)
        assert set(ctrl._registered_modules["ALU"]) == signals

    def test_register_same_signal_for_different_modules(self, ctrl):
        sig = next(iter(signals))
        ctrl.registerForSignal("ALU", sig)
        ctrl.registerForSignal("PC", sig)
        assert sig in ctrl._registered_modules["ALU"]
        assert sig in ctrl._registered_modules["PC"]

    def test_get_signal_state_unknown_signal_raises(self, ctrl):
        with pytest.raises(ValueError):
            ctrl.getSignalState("ALU", "UNKNOWN_SIGNAL")

    def test_get_signal_state_unregistered_module_raises(self, ctrl):
        sig = next(iter(signals))
        with pytest.raises(ValueError):
            ctrl.getSignalState("UNREGISTERED", sig)

    def test_get_signal_state_returns_false_by_default(self, ctrl):
        sig = next(iter(signals))
        ctrl.registerForSignal("ALU", sig)
        assert ctrl.getSignalState("ALU", sig) is False

    def test_get_signal_state_reflects_state_change(self, ctrl):
        sig = next(iter(signals))
        ctrl.registerForSignal("ALU", sig)
        ctrl._signal_state[sig] = True
        assert ctrl.getSignalState("ALU", sig) is True


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


class TestRegister:
    @pytest.fixture
    def ctrl(self):
        return Controller()

    @pytest.fixture
    def bus(self):
        return Bus("Master Bus")

    @pytest.fixture
    def reg(self, bus):
        return Register("RegA", bus, "RAIN", "RAOU")

    def test_is_a_module(self, reg):
        assert isinstance(reg, Module)

    def test_initial_value_is_zero(self, reg):
        assert reg.getValue() == 0

    def test_set_get_value(self, reg):
        reg.setValue(0x42)
        assert reg.getValue() == 0x42

    def test_set_value_masked_to_8_bits(self, reg):
        reg.setValue(0x1FF)
        assert reg.getValue() == 0xFF

    def test_setup_signals_registers_in_and_out(self, reg, ctrl):
        reg.setupSignals(ctrl)
        assert "RAIN" in ctrl._registered_modules["RegA"]
        assert "RAOU" in ctrl._registered_modules["RegA"]

    def test_clock_pulse_outputs_to_bus_when_out_signal_active(self, reg, bus, ctrl):
        reg.setupSignals(ctrl)
        reg.setValue(0xAB)
        ctrl._signal_state["RAOU"] = True
        reg.clock_pulse()
        assert bus.getValue() == 0xAB
        assert bus.getDriver() is reg

    def test_clock_pulse_does_not_drive_bus_when_out_signal_inactive(self, reg, bus, ctrl):
        reg.setupSignals(ctrl)
        reg.setValue(0xAB)
        ctrl._signal_state["RAOU"] = False
        reg.clock_pulse()
        assert bus.getDriver() is None

    def test_clock_inv_pulse_latches_from_bus_when_in_signal_active(self, reg, bus, ctrl):
        reg.setupSignals(ctrl)
        driver = Module("Driver")
        bus.setValue(0x55, driver)
        ctrl._signal_state["RAIN"] = True
        reg.clock_inv_pulse()
        assert reg.getValue() == 0x55

    def test_clock_inv_pulse_does_not_latch_when_in_signal_inactive(self, reg, bus, ctrl):
        reg.setupSignals(ctrl)
        reg.setValue(0x11)
        driver = Module("Driver")
        bus.setValue(0x55, driver)
        ctrl._signal_state["RAIN"] = False
        reg.clock_inv_pulse()
        assert reg.getValue() == 0x11

    def test_clock_pulse_does_nothing_without_controller(self, reg, bus):
        reg.setValue(0xAB)
        reg.clock_pulse()
        assert bus.getDriver() is None

    def test_clock_inv_pulse_does_nothing_without_controller(self, reg, bus):
        reg.setValue(0x11)
        driver = Module("Driver")
        bus.setValue(0x55, driver)
        reg.clock_inv_pulse()
        assert reg.getValue() == 0x11


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

SIZE_BITS = 1024  # 128 bytes


class TestMemory:
    @pytest.fixture
    def ctrl(self):
        return Controller()

    @pytest.fixture
    def bus(self):
        return Bus("Master Bus")

    @pytest.fixture
    def mem(self, bus):
        return Memory("RAM", bus, "RAMI", "RAMO", SIZE_BITS)

    def test_is_a_module(self, mem):
        assert isinstance(mem, Module)

    def test_size_in_bytes(self, mem):
        assert mem.size() == SIZE_BITS // 8

    def test_initial_values_are_zero(self, mem):
        for i in range(mem.size()):
            assert mem.getValue(i) == 0

    def test_set_get_value(self, mem):
        mem.setValue(0, 0xAB)
        assert mem.getValue(0) == 0xAB

    def test_value_masked_to_8_bits(self, mem):
        mem.setValue(0, 0x1FF)
        assert mem.getValue(0) == 0xFF

    def test_clear_resets_all_to_zero(self, mem):
        mem.setValue(0, 0xFF)
        mem.setValue(10, 0x42)
        mem.clear()
        assert mem.getValue(0) == 0
        assert mem.getValue(10) == 0

    def test_address_out_of_range_high_raises(self, mem):
        with pytest.raises(IndexError):
            mem.getValue(SIZE_BITS // 8)

    def test_address_negative_raises(self, mem):
        with pytest.raises(IndexError):
            mem.getValue(-1)

    def test_set_address_out_of_range_raises(self, mem):
        with pytest.raises(IndexError):
            mem.setValue(SIZE_BITS // 8, 0)

    def test_setup_signals_registers_in_and_out(self, mem, ctrl):
        mem.setupSignals(ctrl)
        assert "RAMI" in ctrl._registered_modules["RAM"]
        assert "RAMO" in ctrl._registered_modules["RAM"]

    def test_setup_signals_sets_controller(self, mem, ctrl):
        mem.setupSignals(ctrl)
        assert mem._controller is ctrl

    def test_multiple_addresses_independent(self, mem):
        mem.setValue(0, 0x11)
        mem.setValue(1, 0x22)
        mem.setValue(127, 0xFF)
        assert mem.getValue(0) == 0x11
        assert mem.getValue(1) == 0x22
        assert mem.getValue(127) == 0xFF


# ---------------------------------------------------------------------------
# ALU
# ---------------------------------------------------------------------------


class TestALU:
    @pytest.fixture
    def ctrl(self):
        return Controller()

    @pytest.fixture
    def bus(self):
        return Bus("Master Bus")

    @pytest.fixture
    def reg_a(self, bus):
        return Register("RegisterA", bus, "RAIN", "RAOU")

    @pytest.fixture
    def reg_b(self, bus):
        return Register("RegisterB", bus, "RBIN", "RBOU")

    @pytest.fixture
    def alu(self, bus, reg_a, reg_b, ctrl):
        a = ALU("ALU", bus, reg_a, reg_b, "ALUO", "SUBT")
        a.setupSignals(ctrl)
        return a

    def _set_sub(self, ctrl, on):
        ctrl._signal_state["SUBT"] = on

    def test_is_a_module(self, alu):
        assert isinstance(alu, Module)

    def test_setup_signals_registers_out_and_subtract(self, alu, ctrl):
        assert "ALUO" in ctrl._registered_modules["ALU"]
        assert "SUBT" in ctrl._registered_modules["ALU"]

    def test_initial_value_is_zero(self, alu):
        assert alu.getValue() == 0
        assert alu.zeroFlag() is True
        assert alu.carryFlag() is False

    # --- addition ---------------------------------------------------------

    def test_add(self, alu, reg_a, reg_b):
        reg_a.setValue(5)
        reg_b.setValue(3)
        assert alu.getValue() == 8
        assert alu.carryFlag() is False
        assert alu.zeroFlag() is False

    def test_add_wraps_and_sets_carry(self, alu, reg_a, reg_b):
        reg_a.setValue(200)
        reg_b.setValue(100)
        assert alu.getValue() == (300 & 0xFF)  # 44
        assert alu.carryFlag() is True
        assert alu.zeroFlag() is False

    def test_add_to_zero_sets_carry_and_zero(self, alu, reg_a, reg_b):
        reg_a.setValue(0xFF)
        reg_b.setValue(0x01)
        assert alu.getValue() == 0x00
        assert alu.carryFlag() is True
        assert alu.zeroFlag() is True

    # --- subtraction (two's complement) -----------------------------------

    def test_subtract(self, alu, reg_a, reg_b, ctrl):
        self._set_sub(ctrl, True)
        reg_a.setValue(10)
        reg_b.setValue(3)
        assert alu.getValue() == 7
        assert alu.carryFlag() is True  # no borrow when A >= B
        assert alu.zeroFlag() is False

    def test_subtract_negative_result_twos_complement(self, alu, reg_a, reg_b, ctrl):
        self._set_sub(ctrl, True)
        reg_a.setValue(3)
        reg_b.setValue(10)
        assert alu.getValue() == 0xF9  # -7 in two's complement
        assert alu.carryFlag() is False  # borrow occurred (A < B)
        assert alu.zeroFlag() is False

    def test_subtract_equal_is_zero(self, alu, reg_a, reg_b, ctrl):
        self._set_sub(ctrl, True)
        reg_a.setValue(42)
        reg_b.setValue(42)
        assert alu.getValue() == 0
        assert alu.carryFlag() is True
        assert alu.zeroFlag() is True

    # --- bus interaction --------------------------------------------------

    def test_clock_pulse_drives_bus_when_out_asserted(self, alu, reg_a, reg_b, bus, ctrl):
        reg_a.setValue(20)
        reg_b.setValue(22)
        ctrl._signal_state["ALUO"] = True
        alu.clock_pulse()
        assert bus.getValue() == 42
        assert bus.getDriver() is alu

    def test_clock_pulse_does_not_drive_bus_when_out_inactive(self, alu, reg_a, reg_b, bus, ctrl):
        reg_a.setValue(20)
        reg_b.setValue(22)
        ctrl._signal_state["ALUO"] = False
        alu.clock_pulse()
        assert bus.getDriver() is None

    def test_clock_pulse_drives_subtract_result(self, alu, reg_a, reg_b, bus, ctrl):
        self._set_sub(ctrl, True)
        ctrl._signal_state["ALUO"] = True
        reg_a.setValue(50)
        reg_b.setValue(8)
        alu.clock_pulse()
        assert bus.getValue() == 42


# ---------------------------------------------------------------------------
# FlagsRegister
# ---------------------------------------------------------------------------


class TestFlagsRegister:
    @pytest.fixture
    def ctrl(self):
        return Controller()

    @pytest.fixture
    def bus(self):
        return Bus("Master Bus")

    @pytest.fixture
    def reg_a(self, bus):
        return Register("RegisterA", bus, "RAIN", "RAOU")

    @pytest.fixture
    def reg_b(self, bus):
        return Register("RegisterB", bus, "RBIN", "RBOU")

    @pytest.fixture
    def alu(self, bus, reg_a, reg_b, ctrl):
        a = ALU("ALU", bus, reg_a, reg_b, "ALUO", "SUBT")
        a.setupSignals(ctrl)
        return a

    @pytest.fixture
    def flags(self, alu, ctrl):
        f = FlagsRegister("Flags", alu, "FLGI")
        f.setupSignals(ctrl)
        return f

    def test_is_a_module(self, flags):
        assert isinstance(flags, Module)

    def test_setup_registers_in_signal(self, flags, ctrl):
        assert "FLGI" in ctrl._registered_modules["Flags"]

    def test_initial_flags_false(self, flags):
        assert flags.getCarry() is False
        assert flags.getZero() is False

    def test_latches_carry_and_zero_when_asserted(self, flags, reg_a, reg_b, ctrl):
        reg_a.setValue(0xFF)
        reg_b.setValue(0x01)  # sum 0x00 -> carry and zero
        ctrl._signal_state["FLGI"] = True
        flags.clock_inv_pulse()
        assert flags.getCarry() is True
        assert flags.getZero() is True

    def test_latches_carry_without_zero(self, flags, reg_a, reg_b, ctrl):
        reg_a.setValue(200)
        reg_b.setValue(100)  # sum 44 -> carry, not zero
        ctrl._signal_state["FLGI"] = True
        flags.clock_inv_pulse()
        assert flags.getCarry() is True
        assert flags.getZero() is False

    def test_does_not_latch_when_inactive(self, flags, reg_a, reg_b, ctrl):
        reg_a.setValue(0xFF)
        reg_b.setValue(0x01)
        ctrl._signal_state["FLGI"] = False
        flags.clock_inv_pulse()
        assert flags.getCarry() is False
        assert flags.getZero() is False

    def test_flags_hold_until_next_load(self, flags, reg_a, reg_b, ctrl):
        reg_a.setValue(200)
        reg_b.setValue(100)
        ctrl._signal_state["FLGI"] = True
        flags.clock_inv_pulse()
        # Change the ALU inputs but do not assert FLGI; flags must hold.
        ctrl._signal_state["FLGI"] = False
        reg_a.setValue(1)
        reg_b.setValue(1)
        flags.clock_inv_pulse()
        assert flags.getCarry() is True
        assert flags.getZero() is False

    def test_clear_resets_flags(self, flags, reg_a, reg_b, ctrl):
        reg_a.setValue(0xFF)
        reg_b.setValue(0x01)
        ctrl._signal_state["FLGI"] = True
        flags.clock_inv_pulse()
        flags.clear()
        assert flags.getCarry() is False
        assert flags.getZero() is False


# ---------------------------------------------------------------------------
# RAM
# ---------------------------------------------------------------------------


class TestRAM:
    @pytest.fixture
    def bus(self):
        return Bus("Master Bus")

    @pytest.fixture
    def addr_reg(self, bus):
        return Register("MAR", bus, "MIIN", "MIOU")

    @pytest.fixture
    def ram(self, bus, addr_reg):
        return RAM("RAM", bus, "RAMI", "RAMO", 1024, addr_reg)

    def test_is_a_memory(self, ram):
        assert isinstance(ram, Memory)

    def test_initial_values_are_zero(self, ram):
        for i in range(ram.size()):
            assert ram.getValue(i) == 0

    def test_mem_reg_stored(self, ram, addr_reg):
        assert ram._mem_reg is addr_reg

    def test_load_from_file(self, bus, addr_reg, tmp_path):
        program = bytes([0x01, 0x02, 0x03, 0xFF])
        f = tmp_path / "prog.bin"
        f.write_bytes(program)
        ram = RAM("RAM", bus, "RAMI", "RAMO", 1024, addr_reg, str(f))
        assert ram.getValue(0) == 0x01
        assert ram.getValue(1) == 0x02
        assert ram.getValue(2) == 0x03
        assert ram.getValue(3) == 0xFF

    def test_load_from_file_rest_is_zero(self, bus, addr_reg, tmp_path):
        f = tmp_path / "prog.bin"
        f.write_bytes(bytes([0xAB]))
        ram = RAM("RAM", bus, "RAMI", "RAMO", 1024, addr_reg, str(f))
        assert ram.getValue(0) == 0xAB
        assert ram.getValue(1) == 0x00

    def test_file_too_large_raises(self, bus, addr_reg, tmp_path):
        f = tmp_path / "big.bin"
        f.write_bytes(bytes(200))  # 1024-bit RAM = 128 bytes
        with pytest.raises(ValueError):
            RAM("RAM", bus, "RAMI", "RAMO", 1024, addr_reg, str(f))

    def test_nonexistent_file_raises(self, bus, addr_reg):
        with pytest.raises(FileNotFoundError):
            RAM("RAM", bus, "RAMI", "RAMO", 1024, addr_reg, "/no/such/file.bin")

    def test_no_file_does_not_raise(self, bus, addr_reg):
        RAM("RAM", bus, "RAMI", "RAMO", 1024, addr_reg, "")

    def test_set_and_get_value(self, ram):
        ram.setValue(5, 0xAB)
        assert ram.getValue(5) == 0xAB

    def test_clear_resets_to_zero(self, ram):
        ram.setValue(0, 0xFF)
        ram.clear()
        assert ram.getValue(0) == 0


# ---------------------------------------------------------------------------
# ProgramCounter
# ---------------------------------------------------------------------------


class TestProgramCounter:
    @pytest.fixture
    def bus(self):
        return Bus("Master Bus")

    @pytest.fixture
    def ctrl(self):
        return Controller()

    @pytest.fixture
    def pc(self, bus):
        return ProgramCounter("PC", bus, "JUMP", "PCOU")

    def test_is_a_module(self, pc):
        assert isinstance(pc, Module)

    def test_initial_count_is_zero(self, pc):
        assert pc.getCount() == 0

    def test_reset(self, pc):
        pc.jumpTo(10)
        pc.reset()
        assert pc.getCount() == 0

    def test_jump_to(self, pc):
        pc.jumpTo(42)
        assert pc.getCount() == 42

    def test_jump_to_masked_to_8_bits(self, pc):
        pc.jumpTo(0x1FF)
        assert pc.getCount() == 0xFF

    def test_clock_pulse_increments_count(self, pc, ctrl):
        pc.setupSignals(ctrl)
        pc.clock_pulse()
        assert pc.getCount() == 1

    def test_clock_pulse_wraps_at_256(self, pc, ctrl):
        pc.setupSignals(ctrl)
        pc.jumpTo(0xFF)
        pc.clock_pulse()
        assert pc.getCount() == 0

    def test_clock_pulse_outputs_to_bus_when_pcou_active(self, pc, bus, ctrl):
        pc.setupSignals(ctrl)
        pc.jumpTo(0x0A)
        ctrl._signal_state["PCOU"] = True
        pc.clock_pulse()
        assert bus.getValue() == 0x0A

    def test_clock_pulse_does_not_drive_bus_when_pcou_inactive(self, pc, bus, ctrl):
        pc.setupSignals(ctrl)
        pc.jumpTo(0x0A)
        ctrl._signal_state["PCOU"] = False
        pc.clock_pulse()
        assert bus.getDriver() is None

    def test_clock_inv_pulse_jumps_from_bus_when_jump_active(self, pc, bus, ctrl):
        pc.setupSignals(ctrl)
        driver = Module("Driver")
        bus.setValue(0x20, driver)
        ctrl._signal_state["JUMP"] = True
        pc.clock_inv_pulse()
        assert pc.getCount() == 0x20

    def test_clock_inv_pulse_does_not_jump_when_inactive(self, pc, bus, ctrl):
        pc.setupSignals(ctrl)
        pc.jumpTo(0x05)
        driver = Module("Driver")
        bus.setValue(0x20, driver)
        ctrl._signal_state["JUMP"] = False
        pc.clock_inv_pulse()
        assert pc.getCount() == 0x05

    def test_clock_pulse_outputs_before_incrementing(self, pc, bus, ctrl):
        pc.setupSignals(ctrl)
        pc.jumpTo(0x07)
        ctrl._signal_state["PCOU"] = True
        pc.clock_pulse()
        assert bus.getValue() == 0x07   # value before increment
        assert pc.getCount() == 0x08   # count after increment

    def test_setup_signals_registers_jump_and_pcou(self, pc, ctrl):
        pc.setupSignals(ctrl)
        assert "JUMP" in ctrl._registered_modules["PC"]
        assert "PCOU" in ctrl._registered_modules["PC"]
