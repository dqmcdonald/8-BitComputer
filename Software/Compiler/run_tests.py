#!/usr/bin/env python3
"""
Test runner for the HLL compiler.

Each .hll file in tests/ must contain a line:
    ; EXPECT: v1 v2 ...
The test compiles → assembles → simulates and checks the output values.
"""

import os
import re
import subprocess
import sys
import tempfile

HERE        = os.path.dirname(os.path.abspath(__file__))
COMPILER    = os.path.join(HERE, 'compiler.py')
ASSEMBLER   = os.path.join(HERE, '..', 'Assembler', 'assembler.py')
SIM_DIR     = os.path.join(HERE, '..', 'Simulator')
SIMULATOR   = os.path.join(SIM_DIR, 'simulator.py')
ROM1        = os.path.join(SIM_DIR, 'rom1.bin')
ROM2        = os.path.join(SIM_DIR, 'rom2.bin')
TESTS_DIR   = os.path.join(HERE, 'tests')
CLOCK_SPEED = '100000'


def parse_expected(source: str) -> list[int] | None:
    for line in source.splitlines():
        m = re.match(r';\s*EXPECT:\s*(.*)', line)
        if m:
            return [int(x) for x in m.group(1).split()]
    return None


def run_test(hll_file: str) -> tuple[bool, str]:
    with open(hll_file) as f:
        source = f.read()

    expected = parse_expected(source)
    if expected is None:
        return False, "no EXPECT comment found"

    with (
        tempfile.NamedTemporaryFile(suffix='.asm', delete=False, mode='w') as asm_f,
        tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as bin_f,
    ):
        asm_path = asm_f.name
        bin_path = bin_f.name

    try:
        # Compile HLL → ASM
        r = subprocess.run(
            [sys.executable, COMPILER, hll_file, '-o', asm_path],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return False, f"compile failed:\n{r.stderr.strip()}"

        # Assemble ASM → BIN
        r = subprocess.run(
            [sys.executable, ASSEMBLER, asm_path, '-o', bin_path],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            return False, f"assemble failed:\n{r.stderr.strip()}"

        # Simulate
        r = subprocess.run(
            [sys.executable, SIMULATOR,
             '--prog-rom', bin_path,
             '--rom1', ROM1, '--rom2', ROM2,
             '--speed', CLOCK_SPEED],
            capture_output=True, text=True, timeout=15,
        )
        actual = [
            int(m.group(1))
            for line in r.stdout.splitlines()
            if (m := re.search(r'\*\*\* Output: (\d+)', line))
        ]

        if actual == expected:
            return True, f"output: {actual}"
        return False, f"expected {expected}, got {actual}"

    except subprocess.TimeoutExpired:
        return False, "timed out (possible infinite loop)"
    finally:
        for p in (asm_path, bin_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def main():
    test_files = sorted(
        os.path.join(TESTS_DIR, f)
        for f in os.listdir(TESTS_DIR)
        if f.endswith('.hll')
    )
    if not test_files:
        print(f"No .hll test files found in {TESTS_DIR}")
        sys.exit(1)

    print(f"Running {len(test_files)} tests\n")
    passed = failed = 0
    for hll in test_files:
        name = os.path.basename(hll)
        ok, msg = run_test(hll)
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<35}  {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
