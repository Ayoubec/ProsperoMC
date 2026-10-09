#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Compare translated stack/call behavior with native Linux i386 execution."""
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="pw-x86-reference-") as directory:
    path = Path(directory)
    subprocess.run(["as", "--32", str(root / "tests/test_pw_x86_reference.S"),
                    "-o", str(path / "reference.o")], check=True)
    subprocess.run(["ld", "-m", "elf_i386", "-Ttext=0x01000000",
                    str(path / "reference.o"), "-o", str(path / "reference")], check=True)
    native = subprocess.run([str(path / "reference")], check=True,
                            capture_output=True, timeout=5).stdout
    translated = subprocess.run([str(root / "build/host/test_pw_x86_block"), "--emit"],
                                check=True, capture_output=True, timeout=5).stdout
    # 36 bytes of stack/FS/lock/bit-test values, the 24 bytes of the two
    # LOCK CMPXCHG shapes (word, accumulator and flags each), the 4 bytes of
    # the accumulator's byte forms, the 12 bytes of the memory XCHG (the flags
    # after the exchange, the register and the word) and the 24 bytes of the
    # SSE lane (16 stored bytes, the lane mask and the extracted word).
    assert len(native) == 100 and translated == native, (native.hex(), translated.hex())
print("x86 differential passed: stack/call semantics, 32-bit SIB address wrap, "
      "FS-prefixed absolute operands, lock-prefixed read-modify-write, lock "
      "compare-and-swap to memory in both of its outcomes, the accumulator's "
      "byte forms, exchange with a memory operand leaving the flags alone, bit "
      "test, conditional move and the SSE lane sequence")
