#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Aggregate exact translator coverage from a private Ghidra program.

Raw bytes and assembly remain transient; output contains aggregate counts only.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass

ADDRESS = re.compile(r"^[0-9a-fA-F]{8}$")
BODY_RANGE = re.compile(r"([0-9a-fA-F]{8})\s*-\s*([0-9a-fA-F]{8})")


@dataclass(frozen=True)
class Root:
    address: str
    label: str


class Ghidra:
    def __init__(self, server: str, program: str) -> None:
        self.server, self.program = server.rstrip("/"), program

    def get(self, path: str, **params: object) -> object:
        params["program"] = self.program
        url = self.server + path + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode("utf-8")

    def post(self, path: str, body: dict[str, object]) -> object:
        body["program"] = self.program
        request = urllib.request.Request(
            self.server + path, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())


def reachable(adjacency: dict[str, set[str]], root: str) -> set[str]:
    seen: set[str] = set()
    pending = [root]
    while pending:
        address = pending.pop()
        if address not in seen:
            seen.add(address)
            pending.extend(adjacency.get(address, set()) - seen)
    return seen


def function_instructions(client: Ghidra, address: str) -> list[dict[str, object]]:
    description = client.get("/get_function_by_address", address=address)
    if not isinstance(description, str):
        raise RuntimeError(f"unexpected function description for {address}")
    ranges = BODY_RANGE.findall(description)
    if not ranges:
        raise RuntimeError(f"no body range for {address}")
    result: list[dict[str, object]] = []
    for start, end in ranges:
        extent = {"length": 1} if start == end else {"end_address": end}
        response = client.post("/disassemble_bytes", {
            "start_address": start, **extent,
            "restrict_to_execute_memory": True,
            "include_instructions": True, "max_instructions": 100000,
        })
        if not isinstance(response, dict) or not response.get("success"):
            raise RuntimeError(f"disassembly failed for {address}")
        result.extend(response.get("instructions", []))
    return result


def classify(path: str, instructions: list[dict[str, object]]) -> list[int]:
    payload = "".join(str(item["bytes"]) + "\n" for item in instructions)
    process = subprocess.run([path], input=payload, text=True,
                             capture_output=True, check=True)
    statuses = [int(line) for line in process.stdout.splitlines()]
    if len(statuses) != len(instructions):
        raise RuntimeError("classifier result count differs from instruction count")
    return statuses


def parse_root(value: str) -> Root:
    address, separator, label = value.partition("=")
    if not ADDRESS.fullmatch(address):
        raise argparse.ArgumentTypeError("root must be 8 hex digits[=label]")
    return Root(address.lower(), label if separator else address.lower())


def x87_form(raw: bytes, mnemonic: str) -> str | None:
    """Return a privacy-safe semantic encoding class, not instruction bytes."""
    index = 0
    while index < len(raw) and raw[index] in {
            0x26, 0x2E, 0x36, 0x3E, 0x64, 0x65, 0x66, 0x67,
            0x9B, 0xF0, 0xF2, 0xF3}:
        index += 1
    if index + 1 >= len(raw) or not 0xD8 <= raw[index] <= 0xDF:
        return None
    opcode, modrm = raw[index], raw[index + 1]
    mode, group, operand = modrm >> 6, (modrm >> 3) & 7, modrm & 7
    shape = f"{mnemonic.upper()}:op{opcode - 0xD8}/{'reg' if mode == 3 else 'mem'}/g{group}"
    return shape + (f"/r{operand}" if mode == 3 else "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="http://127.0.0.1:8089")
    parser.add_argument("--program", required=True)
    parser.add_argument("--root", action="append", type=parse_root, required=True)
    parser.add_argument("--classifier", required=True)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    client = Ghidra(args.server, args.program)
    graph = client.get("/get_full_call_graph", format="json_edges", limit=0)
    if not isinstance(graph, dict) or not isinstance(graph.get("edges"), list):
        raise RuntimeError("unexpected call graph response")
    adjacency: dict[str, set[str]] = collections.defaultdict(set)
    for edge in graph["edges"]:
        caller = str(edge["caller_addr"]).lower()
        callee = str(edge["callee_addr"]).lower()
        if ADDRESS.fullmatch(caller) and ADDRESS.fullmatch(callee):
            adjacency[caller].add(callee)

    root_sets = {root.label: reachable(adjacency, root.address) for root in args.root}
    functions = sorted(set().union(*root_sets.values()))
    failures: dict[str, str] = {}
    by_address: dict[str, dict[str, object]] = {}
    function_addresses: dict[str, set[str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(function_instructions, client, address): address
                   for address in functions}
        for future in concurrent.futures.as_completed(futures):
            address = futures[future]
            try:
                items = future.result()
                function_addresses[address] = {
                    str(instruction["address"]).lower() for instruction in items}
                for instruction in items:
                    by_address[str(instruction["address"]).lower()] = instruction
            except Exception as error:
                failures[address] = str(error)
                print(f"coverage omission {address}: {error}", file=sys.stderr)

    instructions = [by_address[key] for key in sorted(by_address)]
    statuses = classify(args.classifier, instructions)
    all_counts: collections.Counter[str] = collections.Counter()
    supported_counts: collections.Counter[str] = collections.Counter()
    unsupported_counts: collections.Counter[str] = collections.Counter()
    x87_total = x87_supported = 0
    x87_forms: collections.Counter[str] = collections.Counter()
    supported_x87_forms: collections.Counter[str] = collections.Counter()
    indirect_calls = indirect_jumps = 0
    status_by_address: dict[str, int] = {}
    for item, status in zip(instructions, statuses):
        status_by_address[str(item["address"]).lower()] = status
        mnemonic = str(item["mnemonic"]).upper()
        all_counts[mnemonic] += 1
        raw = bytes.fromhex(str(item["bytes"]))
        form = x87_form(raw, mnemonic)
        is_x87 = form is not None
        if form:
            x87_total += 1
            x87_forms[form] += 1
        prefix = 0
        while prefix < len(raw) and raw[prefix] in {
                0x26, 0x2E, 0x36, 0x3E, 0x64, 0x65, 0x66, 0x67,
                0xF0, 0xF2, 0xF3}:
            prefix += 1
        if prefix + 1 < len(raw) and raw[prefix] == 0xFF:
            group = (raw[prefix + 1] >> 3) & 7
            indirect_calls += int(group in (2, 3))
            indirect_jumps += int(group in (4, 5))
        if status == 0:
            supported_counts[mnemonic] += 1
            x87_supported += int(is_x87)
            if form:
                supported_x87_forms[form] += 1
        else:
            unsupported_counts[mnemonic] += 1

    total = len(instructions)
    supported = sum(supported_counts.values())
    per_root: dict[str, dict[str, object]] = {}
    for label, nodes in root_sets.items():
        addresses = set().union(*(function_addresses.get(node, set()) for node in nodes))
        root_supported = sum(status_by_address.get(address) == 0
                             for address in addresses)
        root_x87 = collections.Counter(form for form in (
            x87_form(bytes.fromhex(str(by_address[address]["bytes"])),
                     str(by_address[address]["mnemonic"]))
            for address in addresses if address in by_address) if form)
        root_supported_x87 = collections.Counter(form for form in (
            x87_form(bytes.fromhex(str(by_address[address]["bytes"])),
                     str(by_address[address]["mnemonic"]))
            for address in addresses if address in by_address and
            status_by_address.get(address) == 0) if form)
        per_root[label] = {
            "reachable_functions": len(nodes),
            "unique_static_instructions": len(addresses),
            "exact_forms_supported": root_supported,
            "exact_form_coverage_percent": round(
                100.0 * root_supported / len(addresses), 2) if addresses else 0.0,
            "x87_occurrences": sum(root_x87.values()),
            "x87_supported_occurrences": sum(root_supported_x87.values()),
            "x87_unique_forms": len(root_x87),
            "x87_forms": sorted(root_x87.items()),
            "x87_supported_forms": sorted(root_supported_x87.items()),
            "x87_unsupported_forms": sorted((root_x87-root_supported_x87).items()),
        }
    report = {
        "schema": "pw-x86-coverage/3",
        "program": args.program,
        "roots": per_root,
        "reachable_function_union": len(functions),
        "functions_omitted": len(failures),
        "unique_static_instructions": total,
        "exact_forms_supported": supported,
        "exact_forms_unsupported": total - supported,
        "exact_form_coverage_percent": round(100.0 * supported / total, 2) if total else 0.0,
        "x87": {
            "occurrences": x87_total,
            "supported_occurrences": x87_supported,
            "unique_forms": len(x87_forms),
            "top_forms": x87_forms.most_common(30),
            "forms": sorted(x87_forms.items()),
            "supported_forms": sorted(supported_x87_forms.items()),
            "unsupported_forms": sorted((x87_forms-supported_x87_forms).items()),
        },
        "unsupported_non_x87": total - supported - (x87_total - x87_supported),
        "indirect_control_transfers": {
            "calls": indirect_calls, "jumps": indirect_jumps,
        },
        "top_unsupported_mnemonics": unsupported_counts.most_common(20),
        "top_all_mnemonics": all_counts.most_common(20),
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"reachable functions: {len(functions)} ({len(failures)} omitted)")
        print(f"unique static instructions: {total}")
        print(f"exact translator coverage: {supported}/{total} "
              f"({report['exact_form_coverage_percent']:.2f}%)")
        print(f"x87 forms: {x87_supported}/{x87_total}")
        print("top unsupported: " + ", ".join(
            f"{name}={count}" for name, count in unsupported_counts.most_common(20)))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
