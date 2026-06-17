"""
DisassemblerWindow — live program listing with current-PC highlighting.
"""

import tkinter as tk

from instructions import InstructionSet
from simulator import Simulator

# Instructions that consume a following operand byte
_HAS_OPERAND = frozenset({
    InstructionSet.LDA,  InstructionSet.LDB,
    InstructionSet.LDAI, InstructionSet.LDBI,
    InstructionSet.ADDI, InstructionSet.SUBI,
    InstructionSet.STA,  InstructionSet.STB,
    InstructionSet.JMP,  InstructionSet.JMC, InstructionSet.JMZ,
    InstructionSet.CMPI,
})

_ADDR_COLOR = "#5588bb"
_BYTE_COLOR = "#556677"
_MNEM_COLOR = "#ffcc44"
_OP_COLOR   = "#cccccc"
_CUR_BG     = "#1a3a0a"
_CUR_FG     = "#55ff55"


def _disassemble(rom: list[int]) -> list[tuple[int, list[int], str, str]]:
    """
    Walk rom bytes and return (address, raw_bytes, mnemonic, operand_text).
    Stops after HLT or 8 consecutive zero bytes.
    """
    out = []
    pc = 0
    n = len(rom)
    zero_run = 0

    while pc < n:
        op = rom[pc]

        if op == 0:
            zero_run += 1
            if zero_run >= 8:
                break
        else:
            zero_run = 0

        try:
            instr = InstructionSet(op & 0x1F)
        except ValueError:
            out.append((pc, [op], ".byte", f"0x{op:02X}"))
            pc += 1
            continue

        if instr in _HAS_OPERAND and pc + 1 < n:
            operand = rom[pc + 1]
            out.append((pc, [op, operand], instr.name, f"0x{operand:02X} ({operand})"))
            pc += 2
        else:
            out.append((pc, [op], instr.name, ""))
            pc += 1

        if instr == InstructionSet.HLT:
            break

    return out


class DisassemblerWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, sim: Simulator, on_close=None):
        super().__init__(parent)
        self.title("Program Listing")
        self.geometry("360x500")
        self.configure(bg="#0d0d0d")
        self._sim = sim
        self._on_close = on_close
        self._addr_to_line: dict[int, int] = {}  # ROM address → text line number (1-based)
        self._highlighted: int | None = None

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._build()
        self._populate()

    def _build(self):
        frame = tk.Frame(self, bg="#0d0d0d")
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._text = tk.Text(
            frame,
            font=("Courier", 11),
            bg="#0d0d0d", fg=_OP_COLOR,
            selectbackground="#224422",
            state="disabled", wrap="none", cursor="arrow",
        )
        sb = tk.Scrollbar(frame, command=self._text.yview)
        self._text.configure(yscrollcommand=sb.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        self._text.tag_configure("cur",   background=_CUR_BG, foreground=_CUR_FG)
        self._text.tag_configure("addr",  foreground=_ADDR_COLOR)
        self._text.tag_configure("bytes", foreground=_BYTE_COLOR)
        self._text.tag_configure("mnem",  foreground=_MNEM_COLOR)

    def _populate(self):
        rom = self._sim.getProgramBytes()
        listing = _disassemble(rom)

        self._addr_to_line.clear()
        self._text.configure(state="normal")
        self._text.delete("1.0", tk.END)

        if not listing:
            self._text.insert(tk.END, "  (no program loaded)\n", "bytes")
        else:
            for line_num, (addr, raw, mnemonic, operand) in enumerate(listing, start=1):
                self._addr_to_line[addr] = line_num
                bytes_str = " ".join(f"{b:02X}" for b in raw)
                op_str = f" {operand}" if operand else ""
                line = f"{mnemonic:<6}{op_str}\n"
                self._text.insert(tk.END, f"{addr:02X}: ", "addr")
                self._text.insert(tk.END, f"{bytes_str:<6}  ", "bytes")
                self._text.insert(tk.END, line, "mnem")

        self._text.configure(state="disabled")

    def refresh(self):
        pc = self._sim.getProgramCounter()

        if self._highlighted is not None:
            self._text.tag_remove("cur",
                                  f"{self._highlighted}.0",
                                  f"{self._highlighted + 1}.0")

        line = self._addr_to_line.get(pc)
        if line is not None:
            self._text.tag_add("cur", f"{line}.0", f"{line + 1}.0")
            self._text.see(f"{line}.0")
            self._highlighted = line
        else:
            self._highlighted = None

    def _close(self):
        if self._on_close:
            self._on_close()
        self.destroy()
