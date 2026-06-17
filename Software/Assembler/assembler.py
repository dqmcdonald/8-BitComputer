#!/usr/bin/env python3
"""
8-Bit Computer Assembler

Assembles .asm text files into binary programs for the simulator or hardware.

Syntax:
    [LABEL:]  [OPCODE [OPERAND]]  [; comment]

Operands:
    Decimal:    42
    Hex:        0xFF  or  $FF
    Binary:     0b00101010
    Label ref:  LOOP

Sections:
    .code   — instructions and inline data bytes (default if omitted)
    .data   — named variables with initial values

When a .data section is present the assembler emits an initialization preamble
at the start of the ROM that stores each variable's value into RAM before
jumping to the first .code instruction.  This works identically on hardware
and in the simulator; no separate RAM image file is required.

Example:
    .code
            LDB  ONE        ; B = 1
            LDA  COUNT      ; A = RAM[COUNT]
    LOOP:   OUT
            SUB
            JMZ  DONE
            STA  COUNT
            JMP  LOOP
    DONE:   HLT

    .data
    COUNT:  10
    ONE:    1
"""

import argparse
import os
import sys

_SIM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Simulator')
sys.path.insert(0, _SIM_DIR)
from instructions import InstructionSet  # noqa: E402

_HAS_OPERAND: frozenset[InstructionSet] = frozenset({
    InstructionSet.LDA,
    InstructionSet.LDB,
    InstructionSet.LDAI,
    InstructionSet.LDBI,
    InstructionSet.ADDI,
    InstructionSet.SUBI,
    InstructionSet.STA,
    InstructionSet.STB,
    InstructionSet.JMP,
    InstructionSet.JMC,
    InstructionSet.JMZ,
    InstructionSet.CMPI,
})

_OPCODE_MAP: dict[str, InstructionSet] = {i.name: i for i in InstructionSet}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_int(token: str) -> int:
    t = token.strip()
    if t.startswith(('0x', '0X')):
        return int(t, 16)
    if t.startswith(('0b', '0B')):
        return int(t, 2)
    if t.startswith('$'):
        return int(t[1:], 16)
    return int(t, 10)


def _is_label_ref(token: str) -> bool:
    return token[0].isalpha() or token[0] == '_'


def _is_section(line: str) -> bool:
    return line.upper() in ('.CODE', '.DATA')


# ---------------------------------------------------------------------------
# Core assembler — two passes with optional .data section
# ---------------------------------------------------------------------------

def assemble(source: str) -> tuple[bytes, list[str]]:
    """Assemble source text into bytes.

    Returns (binary, errors).  If errors is non-empty the binary is partial
    and should not be used.

    When the source contains a .data section an initialization preamble is
    prepended to the ROM: one LDAI+STA pair per variable, then a JMP to the
    first .code instruction.
    """
    errors: list[str] = []

    # Separate item lists for the two sections
    code_items: list[tuple] = []
    data_decls: list[tuple] = []  # (value, line_num, raw_line)

    code_labels: dict[str, int] = {}  # name -> address within code (before preamble)
    data_labels: dict[str, int] = {}  # name -> index in data_decls

    current_section = 'code'
    code_addr = 0

    # ------------------------------------------------------------------
    # Pass 1: tokenise, assign code addresses, collect data declarations
    # ------------------------------------------------------------------
    for line_num, raw_line in enumerate(source.splitlines(), 1):
        line = raw_line.split(';')[0].strip()
        if not line:
            continue

        if _is_section(line):
            current_section = line[1:].lower()
            continue

        # Extract optional label prefix
        label = None
        if ':' in line:
            label_part, _, rest = line.partition(':')
            label_part = label_part.strip()
            if label_part and all(c.isalnum() or c == '_' for c in label_part):
                label = label_part
                line = rest.strip()
            else:
                errors.append(
                    f"line {line_num}: invalid label '{label_part}'\n"
                    f"    > {raw_line.strip()}"
                )
                continue

        if label:
            if label in code_labels or label in data_labels:
                errors.append(
                    f"line {line_num}: duplicate label '{label}'\n"
                    f"    > {raw_line.strip()}"
                )
            elif current_section == 'code':
                code_labels[label] = code_addr
            else:
                data_labels[label] = len(data_decls)

        if not line:
            continue  # label-only line

        # ---- .data section ----
        if current_section == 'data':
            tokens = line.split()
            try:
                value = _parse_int(tokens[0])
                if not 0 <= value <= 255:
                    errors.append(
                        f"line {line_num}: data value {value} out of range 0-255\n"
                        f"    > {raw_line.strip()}"
                    )
                else:
                    data_decls.append((value, line_num, raw_line))
            except ValueError:
                errors.append(
                    f"line {line_num}: invalid data value '{tokens[0]}'\n"
                    f"    > {raw_line.strip()}"
                )
            continue

        # ---- .code section ----
        tokens = line.split()
        first = tokens[0].upper()

        if first not in _OPCODE_MAP:
            try:
                value = _parse_int(tokens[0])
                if not 0 <= value <= 255:
                    errors.append(
                        f"line {line_num}: data value {value} out of range 0-255\n"
                        f"    > {raw_line.strip()}"
                    )
                else:
                    code_items.append(('raw', code_addr, value, line_num, raw_line))
                    code_addr += 1
            except ValueError:
                errors.append(
                    f"line {line_num}: unknown opcode '{tokens[0]}'\n"
                    f"    > {raw_line.strip()}"
                )
            continue

        instr = _OPCODE_MAP[first]
        needs_operand = instr in _HAS_OPERAND

        if needs_operand and len(tokens) < 2:
            errors.append(
                f"line {line_num}: '{first}' requires an operand\n"
                f"    > {raw_line.strip()}"
            )
            code_addr += 2
            continue
        if not needs_operand and len(tokens) > 1:
            errors.append(
                f"line {line_num}: '{first}' takes no operand (got '{tokens[1]}')\n"
                f"    > {raw_line.strip()}"
            )
            code_addr += 1
            continue

        operand = tokens[1] if needs_operand else None
        code_items.append(('op', code_addr, instr, operand, line_num, raw_line))
        code_addr += 2 if needs_operand else 1

    if errors:
        return b'', errors

    # ------------------------------------------------------------------
    # Compute layout
    # ------------------------------------------------------------------
    has_data = bool(data_decls)
    # Preamble: one LDAI+STA pair per variable, then JMP to code start
    preamble_size = len(data_decls) * 4 + 2 if has_data else 0
    data_start = preamble_size + code_addr

    if data_start + len(data_decls) > 256:
        errors.append(
            f"Program too large: requires {data_start + len(data_decls)} bytes, "
            f"exceeding the 8-bit address space (256 bytes)"
        )
        return b'', errors

    # Build unified label table with final ROM/RAM addresses
    labels: dict[str, int] = {}
    for name, addr in code_labels.items():
        labels[name] = addr + preamble_size
    for name, idx in data_labels.items():
        labels[name] = data_start + idx

    # ------------------------------------------------------------------
    # Pass 2: emit bytes
    # ------------------------------------------------------------------
    output: list[int] = []

    # Preamble: LDAI <value>; STA <ram_addr>  for each data variable, then JMP
    if has_data:
        for i, (value, _, _) in enumerate(data_decls):
            ram_addr = data_start + i
            output.append(int(InstructionSet.LDAI))
            output.append(value)
            output.append(int(InstructionSet.STA))
            output.append(ram_addr)
        output.append(int(InstructionSet.JMP))
        output.append(preamble_size)  # jump to first code instruction

    # Code items
    for item in code_items:
        if item[0] == 'raw':
            _, addr, value, line_num, raw_line = item
            output.append(value)
            continue

        _, addr, instr, operand, line_num, raw_line = item
        output.append(int(instr))

        if operand is not None:
            if _is_label_ref(operand):
                if operand not in labels:
                    errors.append(
                        f"line {line_num}: undefined label '{operand}'\n"
                        f"    > {raw_line.strip()}"
                    )
                    output.append(0)
                else:
                    target = labels[operand]
                    if not 0 <= target <= 255:
                        errors.append(
                            f"line {line_num}: label '{operand}' resolves to address "
                            f"{target} which is out of range 0-255\n"
                            f"    > {raw_line.strip()}"
                        )
                        output.append(0)
                    else:
                        output.append(target)
            else:
                try:
                    value = _parse_int(operand)
                    if not 0 <= value <= 255:
                        errors.append(
                            f"line {line_num}: operand {value} out of range 0-255\n"
                            f"    > {raw_line.strip()}"
                        )
                        output.append(0)
                    else:
                        output.append(value)
                except ValueError:
                    errors.append(
                        f"line {line_num}: invalid operand '{operand}'\n"
                        f"    > {raw_line.strip()}"
                    )
                    output.append(0)

    # Data placeholder bytes at data_start (zero — values are in RAM after preamble runs)
    for _ in data_decls:
        output.append(0)

    if errors:
        return b'', errors

    return bytes(output), []


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

def _count_data_decls(source: str) -> int:
    """Count declared variables in the .data section."""
    count = 0
    in_data = False
    for line in source.splitlines():
        stripped = line.split(';')[0].strip()
        if _is_section(stripped):
            in_data = stripped.upper() == '.DATA'
            continue
        if not in_data or not stripped:
            continue
        content = stripped.partition(':')[2].strip() if ':' in stripped else stripped
        if content:
            count += 1
    return count


def listing(source: str, binary: bytes) -> str:
    """Return a formatted listing: address, bytes, source line."""
    data_count = _count_data_decls(source)
    preamble_size = data_count * 4 + 2 if data_count > 0 else 0

    out: list[str] = []
    binary_pos = 0
    address = 0

    # Show auto-generated preamble
    if preamble_size > 0:
        out.append('; --- auto-generated initialization preamble ---')
        while binary_pos < preamble_size:
            b = binary[binary_pos]
            try:
                op = InstructionSet(b)
                if op in _HAS_OPERAND:
                    op_byte = binary[binary_pos + 1]
                    out.append(f'{address:04X}: {b:02X} {op_byte:02X}    {op.name} {op_byte}')
                    address += 2
                    binary_pos += 2
                else:
                    out.append(f'{address:04X}: {b:02X}       {op.name}')
                    address += 1
                    binary_pos += 1
            except ValueError:
                out.append(f'{address:04X}: {b:02X}')
                address += 1
                binary_pos += 1
        out.append('')

    # Walk source: show code lines with addresses, collect .data lines for end
    data_source_lines: list[str] = []
    in_data = False

    for raw_line in source.splitlines():
        stripped = raw_line.split(';')[0].strip()

        if _is_section(stripped):
            in_data = stripped.upper() == '.DATA'
            out.append(f'          {raw_line}')
            continue

        if in_data:
            data_source_lines.append(raw_line)
            continue

        # Determine byte count for this source line
        nbytes = 0
        if stripped:
            code_line = stripped.partition(':')[2].strip() if ':' in stripped else stripped
            if code_line:
                tokens = code_line.split()
                first = tokens[0].upper()
                if first in _OPCODE_MAP:
                    nbytes = 2 if _OPCODE_MAP[first] in _HAS_OPERAND else 1
                else:
                    try:
                        _parse_int(tokens[0])
                        nbytes = 1
                    except ValueError:
                        pass

        if nbytes:
            byte_str = ' '.join(f'{binary[binary_pos + i]:02X}' for i in range(nbytes))
            out.append(f'{address:04X}: {byte_str:<8}  {raw_line}')
            address += nbytes
            binary_pos += nbytes
        else:
            out.append(f'          {raw_line}')

    # Show .data declarations with their RAM addresses
    if data_source_lines:
        out.append('')
        out.append('; --- .data variables (RAM addresses, initialized by preamble) ---')
        for raw_line in data_source_lines:
            stripped = raw_line.split(';')[0].strip()
            content = stripped.partition(':')[2].strip() if ':' in stripped else stripped
            has_value = False
            if content:
                try:
                    _parse_int(content.split()[0])
                    has_value = True
                except ValueError:
                    pass
            if has_value:
                out.append(f'{address:04X}: 00        {raw_line}')
                address += 1
                binary_pos += 1
            else:
                out.append(f'          {raw_line}')

    return '\n'.join(out)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='8-Bit Computer Assembler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('source', help='Assembly source file')
    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Output binary file (default: source with .bin extension)',
    )
    parser.add_argument(
        '-l', '--list',
        action='store_true',
        help='Print an address/byte listing alongside source lines',
    )
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"error: file not found: '{args.source}'", file=sys.stderr)
        sys.exit(1)

    with open(args.source) as f:
        source = f.read()

    binary, errors = assemble(source)

    if errors:
        print(f"Assembly failed with {len(errors)} error(s):", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(1)

    output_file = args.output or os.path.splitext(args.source)[0] + '.bin'
    with open(output_file, 'wb') as f:
        f.write(binary)

    print(f"Assembled {len(binary)} bytes → '{output_file}'")

    if args.list:
        print()
        print(listing(source, binary))
