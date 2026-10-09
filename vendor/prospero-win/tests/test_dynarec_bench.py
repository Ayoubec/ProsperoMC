#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Deterministic dynarec benchmark regression and one native-i386 cross-check."""
import subprocess
import struct
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "build/host/bench_dynarec"

# Deterministic regression fingerprints for all workloads.  The independent
# native-i386 oracle below currently covers reg_alu; the remaining workloads
# are not claimed as native-oracle comparisons.
EXPECTED = {
    "reg_alu": (0xe44e43d8, 0x00000000, 0x357db716, 0xf2f73b50, 0x50712ee9),
    "cond_branch": (0x00000002, 0x00000000, 0x0002416e, 0x00000000, 0xc8a29443),
    "call_ret": (0x00011171, 0x00000000, 0x00000000, 0x00000000, 0x2133f0d4),
    "mem_load_store": (0x00000000, 0x00000000, 0xa5a5a5a6, 0x00000100, 0x8686ccc1),
    "x87_fp": (0x00000000, 0x00000000, 0x00000000, 0x00000000, 0xb7a17118),
}

# Run benchmark binary
proc = subprocess.run([str(BENCH)], capture_output=True, text=True, check=True)
results = {}
for line in proc.stdout.splitlines():
    if not line.startswith("kind=bench-result"):
        continue
    fields = dict(item.split("=", 1) for item in line.split() if "=" in item)
    name = fields["workload"]
    eax = int(fields["eax"], 16)
    ecx = int(fields["ecx"], 16)
    edx = int(fields["edx"], 16)
    ebx = int(fields["ebx"], 16)
    csum = int(fields["checksum"], 16)
    results[name] = (eax, ecx, edx, ebx, csum)
    exp = EXPECTED[name]
    assert (eax, ecx, edx, ebx) == exp[:4], f"{name} register mismatch: got {(hex(eax), hex(ecx), hex(edx), hex(ebx))} expected {[hex(x) for x in exp[:4]]}"
    assert csum == exp[4], f"{name} checksum mismatch: got {hex(csum)} expected {hex(exp[4])}"

assert results.keys() == EXPECTED.keys(), (
    f"benchmark result set mismatch: got {sorted(results)} expected {sorted(EXPECTED)}"
)

# Verify native Linux i386 oracle matches for reg_alu
with tempfile.TemporaryDirectory(prefix="pw-bench-oracle-") as tmpdir:
    tmppath = Path(tmpdir)
    oracle_s = """
.text
.globl _start
_start:
    movl $0x12345678, %eax
    movl $20000, %ecx
    movl $0xdeadbeef, %edx
    movl $0x00000003, %ebx
loop_start:
    addl $0x1337, %eax
    xorl %eax, %edx
    imull %edx, %ebx
    subl %ebx, %eax
    andl $0x7fffffff, %edx
    orl  $0x10101010, %ebx
    incl %eax
    sarl $1, %edx
    decl %ecx
    jnz loop_start
    pushl %ebx
    pushl %edx
    pushl %ecx
    pushl %eax
    movl %esp, %ecx
    movl $16, %edx
    movl $1, %ebx
    movl $4, %eax
    int $0x80
    movl $0, %ebx
    movl $1, %eax
    int $0x80
"""
    s_path = tmppath / "oracle.s"
    o_path = tmppath / "oracle.o"
    bin_path = tmppath / "oracle"
    s_path.write_text(oracle_s)
    subprocess.run(["as", "--32", str(s_path), "-o", str(o_path)], check=True)
    subprocess.run(["ld", "-m", "elf_i386", str(o_path), "-o", str(bin_path)], check=True)
    out = subprocess.check_output([str(bin_path)])
    native_regs = struct.unpack("<4I", out)
    assert native_regs == EXPECTED["reg_alu"][:4], f"native oracle mismatch: {native_regs}"

print("dynarec benchmark regression passed: 5 deterministic workloads; reg_alu matches native i386")
