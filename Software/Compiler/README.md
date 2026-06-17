# 8-Bit Computer — HLL Compiler

A simple high-level language compiler that targets the 8-bit computer.
Source files are compiled to assembly, which is then assembled and run by
the existing toolchain.

---

## Quick start

```bash
# Compile and run a program
python compiler.py tests/test_01_multiply.hll --run

# Compile to assembly only
python compiler.py myprogram.hll -o myprogram.asm

# Run all compiler tests (compile → assemble → simulate each .hll file)
python run_tests.py
```

---

## Language

Source files use the `.hll` extension. Comments begin with `;`.

### Statements

| Statement | Example | Notes |
|-----------|---------|-------|
| Variable declaration | `let x = 10` | Allocates a RAM variable and sets its initial value |
| Assignment | `x = x + 1` | Right-hand side is an expression |
| Output | `print x` | Sends value to the output register (displays on 7-segment) |
| While loop | `while x != 0` … `end` | Repeats body while condition is true |
| If / else | `if x > y` … `else` … `end` | Conditional block; `else` is optional |

### Expressions

The right-hand side of an assignment or `let` can be:

```
atom            ; a variable or integer literal
atom + atom
atom - atom
atom * atom     ; simulated via repeated addition
```

An `atom` is either an integer literal (`0`–`255`) or a variable name.
Expressions are intentionally flat (no nesting) because the machine has
only two registers.

### Conditions

Used in `while` and `if`:

```
atom == atom
atom != atom
atom <  atom
atom >  atom
atom <= atom
atom >= atom
```

### Example — multiply 6 × 7

```
let a = 6
let b = 7
let result = a * b
print result        ; outputs 42
```

### Example — Fibonacci sequence

```
let prev = 1
let curr = 1
let next = 0

print prev
print curr

while curr < 144
    next = prev + curr
    print next
    prev = curr
    curr = next
end

next = prev + curr
print next
; outputs: 1 1 2 3 5 8 13 21 34 55 89 144 233
```

---

## How multiplication works

The machine has no multiply instruction, so `a * b` is compiled to a
repeated-addition loop using one scratch RAM variable:

```asm
        LDAI  0
        STA   result        ; result = 0
        LDA   b
        STA   _tmp          ; countdown counter = b
        JMZ   done          ; if b == 0, skip
loop:   LDA   result
        LDB   a
        ADD
        STA   result        ; result += a
        LDA   _tmp
        SUBI  1
        STA   _tmp          ; counter--
        JMZ   done
        JMP   loop
done:
```

Multiplication of two 8-bit values can overflow 255; the result wraps
around silently, matching the hardware behaviour.

---

## Compiler pipeline

```
source.hll
    │
    ▼  compiler.py
source.asm          (human-readable assembly)
    │
    ▼  ../Assembler/assembler.py
prog.bin            (flat binary for the program ROM)
    │
    ▼  ../Simulator/simulator.py
output
```

### compiler.py flags

| Flag | Description |
|------|-------------|
| `-o FILE` | Output assembly file (default: source with `.asm` extension) |
| `--run` | Compile, assemble, and run in the simulator immediately |
| `--speed HZ` | Simulator clock speed when using `--run` (default: 100000) |

---

## Tests

```bash
python run_tests.py
```

Each `.hll` file in `tests/` must contain a line of the form:

```
; EXPECT: v1 v2 v3 ...
```

The runner compiles, assembles, simulates, and compares the `OUT` values
against the expected list.

| Test file | What it exercises |
|-----------|------------------|
| `test_01_multiply.hll` | `*` operator (6 × 7 = 42) |
| `test_02_conditionals.hll` | `if`/`else`, `>`, `==`, `while` |
| `test_03_fibonacci.hll` | Fibonacci sequence via `+` and `while` |
| `test_04_primes.hll` | Primes 2–29 via trial division (triple nested loop, modulo via repeated subtraction) |

---

## Limitations

- **No nested expressions** — `a + b * c` is not supported; break it into
  two assignments.
- **No functions** — the machine has no call/return stack.
- **8-bit integers only** — values wrap silently at 255.
- **No arrays** — each variable occupies one RAM byte.
- **~40 variables maximum** — the 8-bit address space is shared with the
  generated program code.
