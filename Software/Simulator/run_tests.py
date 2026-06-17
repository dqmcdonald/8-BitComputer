#!/usr/bin/env python3
"""Test suite for the 8-bit computer simulator.

Each .asm file in the tests/ directory must contain a line of the form:
    ; EXPECT: v1 v2 v3 ...
listing the expected OUT values in order.  The test passes when the
simulator produces exactly those values and halts.
"""

import os
import re
import subprocess
import sys
import tempfile

SIMULATOR_DIR = os.path.dirname(os.path.abspath(__file__))
ASSEMBLER     = os.path.join(SIMULATOR_DIR, '..', 'Assembler', 'assembler.py')
SIMULATOR     = os.path.join(SIMULATOR_DIR, 'simulator.py')
TESTS_DIR     = os.path.join(SIMULATOR_DIR, 'tests')
CLOCK_SPEED   = '100000'   # Hz — fast enough to finish quickly


def parse_expected(source: str) -> list[int] | None:
    for line in source.splitlines():
        m = re.match(r';\s*EXPECT:\s*(.*)', line)
        if m:
            return [int(x) for x in m.group(1).split()]
    return None


def run_test(asm_file: str) -> tuple[bool, str]:
    with open(asm_file) as f:
        source = f.read()

    expected = parse_expected(source)
    if expected is None:
        return False, "no EXPECT comment found"

    with tempfile.NamedTemporaryFile(suffix='.bin', delete=False) as tmp:
        bin_file = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, ASSEMBLER, asm_file, '-o', bin_file],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return False, f"assembly failed:\n{result.stderr.strip()}"

        result = subprocess.run(
            [sys.executable, SIMULATOR,
             '--prog-rom', bin_file,
             '--mode', 'continuous',
             '--speed', CLOCK_SPEED],
            capture_output=True, text=True, timeout=15,
        )

        actual = [
            int(m.group(1))
            for line in result.stdout.splitlines()
            if (m := re.search(r'\*\*\* Output: (\d+)', line))
        ]

        if actual == expected:
            return True, f"output: {actual}"
        return False, f"expected {expected}, got {actual}"

    except subprocess.TimeoutExpired:
        return False, "timed out (possible infinite loop)"
    finally:
        os.unlink(bin_file)


def main() -> None:
    test_files = sorted(
        os.path.join(TESTS_DIR, f)
        for f in os.listdir(TESTS_DIR)
        if f.endswith('.asm')
    )

    if not test_files:
        print(f"No test files found in {TESTS_DIR}")
        sys.exit(1)

    print(f"Running {len(test_files)} tests\n")

    passed = failed = 0
    for asm_file in test_files:
        name = os.path.basename(asm_file)
        ok, msg = run_test(asm_file)
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {name:<35}  {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
