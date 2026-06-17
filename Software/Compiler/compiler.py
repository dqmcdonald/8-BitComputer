#!/usr/bin/env python3
"""
compiler.py — tiny compiler targeting the 8-bit computer.

Language (one statement per line, ; starts a comment):

    let name = expr
    name = expr
    print expr
    while cond
        ...
    end
    if cond
        ...
    [else
        ...]
    end

expr  :  atom  |  atom OP atom          (OP = + - *)
atom  :  INTEGER  |  IDENTIFIER
cond  :  atom RELOP atom                (RELOP = == != < > <= >=)

Output: assembly text ready for the existing assembler.

Usage:
    python compiler.py source.hll [-o out.asm]
    python compiler.py source.hll --run   # compile, assemble and simulate
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Union

# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

KEYWORDS = {'let', 'print', 'while', 'if', 'else', 'end'}


@dataclass
class Token:
    kind: str       # keyword, 'INT', 'IDENT', operator string, or 'EOF'
    value: object   # int for INT, str otherwise
    line: int


def tokenize(src: str) -> list[Token]:
    toks: list[Token] = []
    i, line = 0, 1
    n = len(src)
    while i < n:
        c = src[i]
        if c in ' \t\r':
            i += 1
        elif c == ';':                          # line comment
            while i < n and src[i] != '\n':
                i += 1
        elif c == '\n':
            line += 1
            i += 1
        elif c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            toks.append(Token('INT', int(src[i:j]), line))
            i = j
        elif c.isalpha() or c == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'):
                j += 1
            word = src[i:j]
            toks.append(Token(word if word in KEYWORDS else 'IDENT', word, line))
            i = j
        elif src[i:i+2] in ('==', '!=', '<=', '>='):
            toks.append(Token(src[i:i+2], src[i:i+2], line))
            i += 2
        elif c in '+-*=<>':
            toks.append(Token(c, c, line))
            i += 1
        else:
            raise SyntaxError(f"line {line}: unexpected character {c!r}")
    toks.append(Token('EOF', None, line))
    return toks


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

@dataclass
class Literal:
    value: int

@dataclass
class Var:
    name: str

Atom = Union[Literal, Var]

@dataclass
class BinOp:
    left: Atom
    op: str          # '+' | '-' | '*'
    right: Atom

Expr = Union[Atom, BinOp]

@dataclass
class Condition:
    left: Atom
    op: str          # '==' | '!=' | '<' | '>' | '<=' | '>='
    right: Atom

@dataclass
class LetStmt:
    name: str
    expr: Expr

@dataclass
class AssignStmt:
    name: str
    expr: Expr

@dataclass
class PrintStmt:
    expr: Atom

@dataclass
class WhileStmt:
    cond: Condition
    body: list

@dataclass
class IfStmt:
    cond: Condition
    then_body: list
    else_body: list

Stmt = Union[LetStmt, AssignStmt, PrintStmt, WhileStmt, IfStmt]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: list[Token]):
        self._t = tokens
        self._i = 0

    def _peek(self) -> Token:
        return self._t[self._i]

    def _eat(self, kind: str) -> Token:
        tok = self._t[self._i]
        if tok.kind != kind:
            raise SyntaxError(
                f"line {tok.line}: expected {kind!r}, got {tok.kind!r} ({tok.value!r})"
            )
        self._i += 1
        return tok

    def _match(self, kind: str) -> bool:
        if self._t[self._i].kind == kind:
            self._i += 1
            return True
        return False

    def parse(self) -> list[Stmt]:
        stmts = self._parse_block(stop=('EOF',))
        self._eat('EOF')
        return stmts

    def _parse_block(self, stop: tuple) -> list[Stmt]:
        stmts = []
        while self._peek().kind not in stop:
            stmts.append(self._parse_stmt())
        return stmts

    def _parse_stmt(self) -> Stmt:
        tok = self._peek()
        if tok.kind == 'let':
            return self._parse_let()
        if tok.kind == 'print':
            return self._parse_print()
        if tok.kind == 'while':
            return self._parse_while()
        if tok.kind == 'if':
            return self._parse_if()
        if tok.kind == 'IDENT':
            return self._parse_assign()
        raise SyntaxError(f"line {tok.line}: unexpected {tok.value!r}")

    def _parse_let(self) -> LetStmt:
        self._eat('let')
        name = self._eat('IDENT').value
        self._eat('=')
        return LetStmt(name, self._parse_expr())

    def _parse_assign(self) -> AssignStmt:
        name = self._eat('IDENT').value
        self._eat('=')
        return AssignStmt(name, self._parse_expr())

    def _parse_print(self) -> PrintStmt:
        self._eat('print')
        return PrintStmt(self._parse_atom())

    def _parse_while(self) -> WhileStmt:
        self._eat('while')
        cond = self._parse_cond()
        body = self._parse_block(stop=('end', 'EOF'))
        self._eat('end')
        return WhileStmt(cond, body)

    def _parse_if(self) -> IfStmt:
        self._eat('if')
        cond = self._parse_cond()
        then_body = self._parse_block(stop=('else', 'end', 'EOF'))
        else_body: list[Stmt] = []
        if self._match('else'):
            else_body = self._parse_block(stop=('end', 'EOF'))
        self._eat('end')
        return IfStmt(cond, then_body, else_body)

    def _parse_cond(self) -> Condition:
        left = self._parse_atom()
        tok = self._peek()
        if tok.kind not in ('==', '!=', '<', '>', '<=', '>='):
            raise SyntaxError(f"line {tok.line}: expected comparison operator, got {tok.value!r}")
        self._i += 1
        right = self._parse_atom()
        return Condition(left, tok.kind, right)

    def _parse_expr(self) -> Expr:
        left = self._parse_atom()
        if self._peek().kind in ('+', '-', '*'):
            op = self._t[self._i].kind
            self._i += 1
            return BinOp(left, op, self._parse_atom())
        return left

    def _parse_atom(self) -> Atom:
        tok = self._peek()
        if tok.kind == 'INT':
            self._i += 1
            return Literal(tok.value)
        if tok.kind == 'IDENT':
            self._i += 1
            return Var(tok.value)
        raise SyntaxError(f"line {tok.line}: expected value, got {tok.value!r}")


# ---------------------------------------------------------------------------
# Code generator
# ---------------------------------------------------------------------------

class CodeGen:
    def __init__(self):
        self._vars:      dict[str, str] = {}  # user name → asm label
        self._data_vars: list[str]      = []  # all RAM labels (in declaration order)
        self._label_n = 0
        self._lines:  list[str] = []

    # ---- helpers --------------------------------------------------------

    def _vlabel(self, name: str) -> str:
        """Return (and register) the asm label for a user variable."""
        if name not in self._vars:
            lbl = f"_v_{name}"
            self._vars[name] = lbl
            self._data_vars.append(lbl)
        return self._vars[name]

    def _new_label(self, prefix: str) -> str:
        lbl = f"__{prefix}_{self._label_n}"
        self._label_n += 1
        return lbl

    def _new_tmp(self) -> str:
        """Allocate a new anonymous RAM temp variable."""
        lbl = f"_tmp{len(self._data_vars)}"
        self._data_vars.append(lbl)
        return lbl

    def _emit(self, s: str):
        self._lines.append(s)

    # ---- load helpers ---------------------------------------------------

    def _load_a(self, atom: Atom):
        if isinstance(atom, Literal):
            self._emit(f"        LDAI  {atom.value}")
        else:
            self._emit(f"        LDA   {self._vlabel(atom.name)}")

    def _load_b(self, atom: Atom):
        if isinstance(atom, Literal):
            self._emit(f"        LDBI  {atom.value}")
        else:
            self._emit(f"        LDB   {self._vlabel(atom.name)}")

    # ---- condition: jump to `label` when condition is FALSE -------------

    def _jump_if_false(self, cond: Condition, label: str):
        left, op, right = cond.left, cond.op, cond.right

        # --- general: load A = left, compute A − right via CMP/CMPI ---
        # NOTE: LDA alone does not update the zero flag; we always use CMP/CMPI
        # so the flags reflect the actual current value of left.
        self._load_a(left)
        if isinstance(right, Literal):
            self._emit(f"        CMPI  {right.value}")
        else:
            self._load_b(right)
            self._emit(f"        CMP")

        # After CMP/CMPI: carry=1 ⟺ A≥right, zero=1 ⟺ A==right
        if op == '==':
            # false (jump) when not equal
            skip = self._new_label('SK')
            self._emit(f"        JMZ   {skip}")
            self._emit(f"        JMP   {label}")
            self._emit(f"{skip}:")
        elif op == '!=':
            # false (jump) when equal
            self._emit(f"        JMZ   {label}")
        elif op == '>=':
            # false when A < right  (carry=0)
            skip = self._new_label('SK')
            self._emit(f"        JMC   {skip}")
            self._emit(f"        JMP   {label}")
            self._emit(f"{skip}:")
        elif op == '<':
            # false when A >= right (carry=1)
            self._emit(f"        JMC   {label}")
        elif op == '>':
            # false when A <= right (zero=1 or carry=0)
            skip = self._new_label('SK')
            self._emit(f"        JMZ   {label}")       # equal → not >
            self._emit(f"        JMC   {skip}")        # carry + non-zero → A > right
            self._emit(f"        JMP   {label}")       # no carry → A < right
            self._emit(f"{skip}:")
        elif op == '<=':
            # false when A > right  (carry=1 and zero=0)
            skip = self._new_label('SK')
            self._emit(f"        JMZ   {skip}")        # equal → ≤, skip exit
            self._emit(f"        JMC   {label}")       # carry + non-zero → A > right
            self._emit(f"{skip}:")

    # ---- expression code generation -------------------------------------

    def _gen_expr(self, expr: Expr, dest: str):
        """Generate code that computes expr and stores the result in dest."""
        if isinstance(expr, Literal):
            self._emit(f"        LDAI  {expr.value}")
            self._emit(f"        STA   {dest}")
        elif isinstance(expr, Var):
            self._emit(f"        LDA   {self._vlabel(expr.name)}")
            self._emit(f"        STA   {dest}")
        elif isinstance(expr, BinOp):
            if expr.op == '+':
                self._load_a(expr.left)
                if isinstance(expr.right, Literal):
                    self._emit(f"        ADDI  {expr.right.value}")
                else:
                    self._load_b(expr.right)
                    self._emit(f"        ADD")
                self._emit(f"        STA   {dest}")
            elif expr.op == '-':
                self._load_a(expr.left)
                if isinstance(expr.right, Literal):
                    self._emit(f"        SUBI  {expr.right.value}")
                else:
                    self._load_b(expr.right)
                    self._emit(f"        SUB")
                self._emit(f"        STA   {dest}")
            elif expr.op == '*':
                self._gen_multiply(expr.left, expr.right, dest)

    def _gen_multiply(self, left: Atom, right: Atom, dest: str):
        """
        Simulate dest = left * right via repeated addition.
        Uses two temp RAM variables so dest may safely alias left or right.
        """
        tmp_left    = self._new_tmp()   # saved copy of left operand
        tmp_counter = self._new_tmp()   # countdown = right
        loop = self._new_label('MUL')
        done = self._new_label('MULD')

        # Save left before zeroing dest (dest may be the same RAM cell as left)
        self._load_a(left)
        self._emit(f"        STA   {tmp_left}")
        self._emit(f"        LDAI  0")
        self._emit(f"        STA   {dest}")         # dest = 0
        self._load_a(right)
        self._emit(f"        STA   {tmp_counter}")  # counter = right
        self._emit(f"        JMZ   {done}")         # if right == 0, skip
        self._emit(f"{loop}:")
        self._emit(f"        LDA   {dest}")
        self._emit(f"        LDB   {tmp_left}")
        self._emit(f"        ADD")
        self._emit(f"        STA   {dest}")         # dest += left
        self._emit(f"        LDA   {tmp_counter}")
        self._emit(f"        SUBI  1")
        self._emit(f"        STA   {tmp_counter}")  # counter--
        self._emit(f"        JMZ   {done}")         # if counter == 0, done
        self._emit(f"        JMP   {loop}")
        self._emit(f"{done}:")

    # ---- statement code generation --------------------------------------

    def gen_stmts(self, stmts: list[Stmt]):
        for stmt in stmts:
            self._gen_stmt(stmt)

    def _gen_stmt(self, stmt: Stmt):
        if isinstance(stmt, (LetStmt, AssignStmt)):
            dest = self._vlabel(stmt.name)
            self._gen_expr(stmt.expr, dest)
        elif isinstance(stmt, PrintStmt):
            self._load_a(stmt.expr)
            self._emit(f"        OUT")
        elif isinstance(stmt, WhileStmt):
            top  = self._new_label('WHILE')
            done = self._new_label('WEND')
            self._emit(f"{top}:")
            self._jump_if_false(stmt.cond, done)
            self.gen_stmts(stmt.body)
            self._emit(f"        JMP   {top}")
            self._emit(f"{done}:")
        elif isinstance(stmt, IfStmt):
            else_lbl = self._new_label('ELSE')
            end_lbl  = self._new_label('ENDIF')
            self._jump_if_false(stmt.cond, else_lbl)
            self.gen_stmts(stmt.then_body)
            if stmt.else_body:
                self._emit(f"        JMP   {end_lbl}")
            self._emit(f"{else_lbl}:")
            if stmt.else_body:
                self.gen_stmts(stmt.else_body)
                self._emit(f"{end_lbl}:")

    # ---- final assembly output ------------------------------------------

    def output(self, source_name: str = "") -> str:
        hdr = f"; Generated by compiler.py"
        if source_name:
            hdr += f" from {source_name}"
        parts = [hdr, ""]

        parts += [".code"]
        parts += self._lines
        parts += ["        HLT", ""]

        if self._data_vars:
            parts += [".data"]
            for lbl in self._data_vars:
                parts.append(f"{lbl}:  0")

        return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Top-level compile function
# ---------------------------------------------------------------------------

def compile_source(src: str, source_name: str = "") -> str:
    tokens = tokenize(src)
    stmts  = Parser(tokens).parse()
    cg     = CodeGen()
    cg.gen_stmts(stmts)
    return cg.output(source_name)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="8-bit computer HLL compiler")
    ap.add_argument("source", help="Source file (.hll)")
    ap.add_argument("-o", "--output", default="", metavar="FILE",
                    help="Output assembly file (default: source with .asm extension)")
    ap.add_argument("--run", action="store_true",
                    help="Assemble and run in the simulator after compiling")
    ap.add_argument("--speed", type=float, default=100000,
                    help="Simulator speed in Hz when --run is used (default: 100000)")
    args = ap.parse_args()

    with open(args.source) as f:
        src = f.read()

    try:
        asm = compile_source(src, os.path.basename(args.source))
    except SyntaxError as e:
        print(f"Compile error: {e}", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or os.path.splitext(args.source)[0] + ".asm"
    with open(out_path, "w") as f:
        f.write(asm)
    print(f"Written: {out_path}")

    if args.run:
        here       = os.path.dirname(os.path.abspath(__file__))
        assembler  = os.path.join(here, '..', 'Assembler', 'assembler.py')
        sim_dir    = os.path.join(here, '..', 'Simulator')
        simulator  = os.path.join(sim_dir, 'simulator.py')
        rom1       = os.path.join(sim_dir, 'rom1.bin')
        rom2       = os.path.join(sim_dir, 'rom2.bin')

        with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp:
            bin_path = tmp.name
        try:
            r = subprocess.run(
                [sys.executable, assembler, out_path, '-o', bin_path],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                print(f"Assembly failed:\n{r.stderr.strip()}", file=sys.stderr)
                sys.exit(1)

            r = subprocess.run(
                [sys.executable, simulator,
                 '--prog-rom', bin_path,
                 '--rom1', rom1, '--rom2', rom2,
                 '--speed', str(args.speed)],
                capture_output=True, text=True, timeout=30,
            )
            for line in r.stdout.splitlines():
                if '*** Output:' in line:
                    print(line)
        finally:
            os.unlink(bin_path)


if __name__ == '__main__':
    main()
