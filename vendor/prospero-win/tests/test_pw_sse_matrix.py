#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Every accepted 0f form, compared against the host CPU.

The C harness (``test_pw_x86_block --sse-matrix``) enumerates the forms the
translator accepts - the 0f space carries SSE, BT/BTS/BTR/BTC, CMOVcc and
BSF/BSR - runs each one in its register and its memory form through all four
engine mode combinations, and prints the initial state followed by the state
after every form. This script assembles the *same instruction bytes* natively,
runs them with the same initial state (the harness's own header, replayed into
the generated program), and compares the resulting state byte for byte.

So the oracle is the CPU executing an independent program, not the instruction
the translator emitted. Two defects were found this way: PMOVMSKB accepting a
memory operand the ISA does not have (a host sigill) and the bit-test family
validating the base address while the CPU reads the bit-string unit
``base + width*(offset DIV (width*8))``.

What the comparison covers, exactly: the two runners have different stacks by
construction (the native program runs on one it restores per form, the harness
on the guest stack), so the ESP word is not compared for any form. That means
the one accepted form that *writes* ESP, `bswap esp` (`0f cc`), has its ESP
effect excluded rather than checked, and it is listed explicitly below so a
second one cannot appear unnoticed; every other effect of that form, and every
effect of every other form, is compared byte for byte. Defined EFLAGS effects
(the bit-test, BSF/BSR and CMOVcc families) are not part of this state, so they
keep their own tests in tests/test_pw_x86_block.c - this oracle is a data-state
oracle and does not claim to be an instruction-effects oracle.
"""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "build/host/test_pw_x86_block"

GPR_BYTES = 32
XMM_BYTES = 128
WINDOW_BYTES = 64
STATE_BYTES = GPR_BYTES + XMM_BYTES + WINDOW_BYTES
DESCRIPTOR_BYTES = 5
ESP_OFFSET = 16
ESP_END = ESP_OFFSET + 4
WINDOW_ADDRESS = 0x03000800
# The accepted forms that write ESP, whose stack effect this oracle cannot
# compare (see the module docstring).
ESP_WRITERS = {bytes([0x0f, 0xcc]): "bswap esp"}


def run_matrix() -> bytes:
    return subprocess.run([str(RUNNER), "--sse-matrix"], check=True,
                          capture_output=True, timeout=120).stdout


def parse(blob: bytes) -> tuple[bytes, list[tuple[bytes, bytes]]]:
    assert len(blob) > STATE_BYTES, "the matrix printed no state header"
    header, body = blob[:STATE_BYTES], blob[STATE_BYTES:]
    records: list[tuple[bytes, bytes | None]] = []
    offset = 0
    while offset < len(body):
        descriptor = body[offset:offset + DESCRIPTOR_BYTES]
        assert len(descriptor) == DESCRIPTOR_BYTES, offset
        offset += DESCRIPTOR_BYTES
        form, executed = descriptor[:4], descriptor[4]
        if not executed:
            records.append((form, None))
            continue
        state = body[offset:offset + STATE_BYTES]
        assert len(state) == STATE_BYTES, offset
        offset += STATE_BYTES
        records.append((form, state))
    return header, records


def movl(register: str, value: int) -> str:
    return f"    movl $0x{value:08x}, %{register}"


def instruction_bytes(form: bytes) -> bytes:
    """The instruction a form describes, using the translator's own length."""
    prefix, opcode, modrm, length = form
    base = 1 if prefix else 0
    instruction = bytes([prefix]) if prefix else b""
    instruction += bytes([0x0f, opcode])
    if length >= base + 3:
        instruction += bytes([modrm])
    if length >= base + 4:
        instruction += bytes([0x03])
    assert len(instruction) == length, (form.hex(), length)
    return instruction


def generate(header: bytes, forms: list[bytes]) -> str:
    gprs = struct.unpack("<8I", header[:GPR_BYTES])
    xmm = header[GPR_BYTES:GPR_BYTES + XMM_BYTES]
    window = header[GPR_BYTES + XMM_BYTES:]
    registers = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]
    lines = [
        "    .text",
        "    .globl _start",
        "_start:",
        "    /* Map one page at the window base so both programs use the same",
        "     * absolute address for every memory operand. */",
        "    movl $192, %eax",                    # mmap2
        f"    movl $0x{WINDOW_ADDRESS & ~0xfff:08x}, %ebx",
        "    movl $4096, %ecx",
        "    movl $3, %edx",                      # PROT_READ|PROT_WRITE
        "    movl $0x32, %esi",                   # PRIVATE|FIXED|ANONYMOUS
        "    movl $-1, %edi",
        "    xorl %ebp, %ebp",
        "    int $0x80",
        "    /* A private stack: a form may write ESP (bswap esp is a legal",
        "     * guest instruction), and the oracle must survive it. */",
        "    movl $oracle_stack_top, %esp",
    ]
    for index, form in enumerate(forms):
        out = index * STATE_BYTES
        instruction = instruction_bytes(form)
        lines.append(f"    /* form {index}: {bytes(instruction).hex(' ')} */")
        # The window first: copying it uses XMM7, which is loaded afterwards.
        for offset in range(0, WINDOW_BYTES, 16):
            lines.append(f"    movdqu win_init+{offset}, %xmm7")
            lines.append(f"    movdqu %xmm7, {WINDOW_ADDRESS + offset:#x}")
        for register, value in zip(registers, gprs):
            if register == "esp":                # the process stack is not
                continue                         # the harness's
            lines.append(movl(register, value))
        # Restore the private stack before touching it again: the previous
        # form may have written ESP, and this is also where the guest flags
        # start from zero for the flags-reading forms (CMOVcc).
        lines.append("    movl $oracle_stack_top, %esp")
        lines.append("    pushl $0")             # guest EFLAGS start at zero
        lines.append("    popfl")
        for register in range(8):
            lines.append(f"    movdqu xmm_init+{register * 16}, %xmm{register}")
        lines.append("    .byte " + ", ".join(f"{byte:#04x}"
                                              for byte in instruction))
        for index_in_state, register in enumerate(registers):
            lines.append(f"    movl %{register}, out+{out + index_in_state * 4}")
        for register in range(8):
            lines.append(f"    movdqu %xmm{register}, out+{out + 32 + register * 16}")
        for offset in range(0, WINDOW_BYTES, 16):
            lines.append(f"    movdqu {WINDOW_ADDRESS + offset:#x}, %xmm7")
            lines.append(f"    movdqu %xmm7, out+{out + 160 + offset}")
    total = len(forms) * STATE_BYTES
    lines += [
        "    movl $4, %eax",                      # write
        "    movl $1, %ebx",
        "    movl $out, %ecx",
        f"    movl ${total}, %edx",
        "    int $0x80",
        "    movl $1, %eax",                      # exit
        "    xorl %ebx, %ebx",
        "    int $0x80",
        "    .section .rodata",
        "xmm_init:",
        "    .byte " + ", ".join(str(byte) for byte in xmm),
        "win_init:",
        "    .byte " + ", ".join(str(byte) for byte in window),
        "    .bss",
        "    .lcomm oracle_stack, 4096",
        "    .set oracle_stack_top, oracle_stack + 4096",
        f"    .lcomm out, {total}",
    ]
    return "\n".join(lines) + "\n"


def run_native(asm: str, forms: int) -> bytes:
    with tempfile.TemporaryDirectory(prefix="/tmp/pw-sse-matrix-") as directory:
        path = Path(directory)
        (path / "oracle.S").write_text(asm)
        subprocess.run(["as", "--32", str(path / "oracle.S"),
                        "-o", str(path / "oracle.o")], check=True)
        subprocess.run(["ld", "-m", "elf_i386", "-Ttext=0x08048000",
                        "-e", "_start", str(path / "oracle.o"),
                        "-o", str(path / "oracle")], check=True)
        return subprocess.run([str(path / "oracle")], check=True,
                              capture_output=True, timeout=60).stdout


def compare(instruction: bytes, translated: bytes, native: bytes,
            problems: list[str]) -> None:
    for name, start, end in (("gprs", 0, GPR_BYTES),
                             ("xmm", GPR_BYTES, GPR_BYTES + XMM_BYTES),
                             ("window", GPR_BYTES + XMM_BYTES, STATE_BYTES)):
        left, right = translated[start:end], native[start:end]
        if start == 0:
            # ESP only: the two programs have different stacks by design.
            left, right = left[:ESP_OFFSET] + left[ESP_END:], \
                          right[:ESP_OFFSET] + right[ESP_END:]
        if left != right:
            problems.append(f"{instruction.hex(' ')} {name}: translated "
                            f"{left.hex()} vs native {right.hex()}")


def main() -> int:
    header, records = parse(run_matrix())
    executed = [(form, state) for form, state in records if state is not None]
    refused = [form for form, state in records if state is None]
    assert len(executed) > 50, f"only {len(executed)} forms executed"
    writers = sorted({ESP_WRITERS[bytes(instruction_bytes(form))]
                      for form, _ in executed
                      if bytes(instruction_bytes(form)) in ESP_WRITERS})
    assert writers == sorted(ESP_WRITERS.values()), (
        "the set of ESP-writing forms changed: " f"{writers}")
    asm = generate(header, [form for form, _ in executed])
    native = run_native(asm, len(executed))
    assert len(native) == len(executed) * STATE_BYTES, len(native)

    problems: list[str] = []
    for index, (form, translated) in enumerate(executed):
        compare(instruction_bytes(form), translated,
                native[index * STATE_BYTES:(index + 1) * STATE_BYTES],
                problems)
    if problems:
        raise SystemExit("SSE form matrix failed:\n  " + "\n  ".join(problems))
    print(f"SSE form matrix passed: {len(executed)} forms in register and "
          f"memory form against the host CPU in four engine modes "
          f"({len(refused)} refused by the guard for an operand the initial "
          f"state sends out of the window; ESP excluded, including "
          f"{', '.join(writers)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
