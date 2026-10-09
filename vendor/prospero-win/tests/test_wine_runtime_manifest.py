#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Adversarial tests for the staged Wine runtime manifest contract.

The manifest is the identity other stages bind against, so every way of
substituting or mis-describing a module has to fail closed: a wrong machine,
a renamed file, a traversal path, a stale hash, a duplicate name or a
manifest whose aggregate digest does not match its own module list.
"""

from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import make_test_pe  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "wine_runtime_validator", ROOT / "tools/validate_wine_runtime.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

LIBRARY = "lib/i386-windows"
COMMIT = "490f6d5dcbb2a5047345b8af88d114bbcaad69a8"


def pe32_image(name: str, machine: int = make_test_pe.MACHINE_I386) -> bytes:
    spec = make_test_pe.Spec(
        name=name,
        pe32plus=False,
        machine=machine,
        dll=True,
        sections=[make_test_pe.Section(
            ".text",
            make_test_pe.SCN_CNT_CODE | make_test_pe.SCN_MEM_READ |
            make_test_pe.SCN_MEM_EXECUTE,
            bytes([0x31, 0xC0, 0xC3]),)],
    )
    return make_test_pe.build_pe(spec)


def pe64_image(name: str) -> bytes:
    spec = make_test_pe.Spec(
        name=name,
        pe32plus=True,
        dll=True,
        sections=[make_test_pe.Section(
            ".text",
            make_test_pe.SCN_CNT_CODE | make_test_pe.SCN_MEM_READ |
            make_test_pe.SCN_MEM_EXECUTE,
            bytes([0x48, 0x31, 0xC0, 0xC3]),)],
    )
    return make_test_pe.build_pe(spec)


class Case(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = Path(tempfile.mkdtemp(prefix="wine-runtime-"))
        self.distribution = self.temporary / "distribution"
        (self.distribution / LIBRARY).mkdir(parents=True)
        self.write_module("ntdll.dll", pe32_image("ntdll.dll"))
        self.write_module("kernel32.dll", pe32_image("kernel32.dll"))
        self.source = self.temporary / "wine"
        self.source.mkdir()
        (self.source / "VERSION").write_text("Wine version 11.17\n",
                                             encoding="utf-8")
        subprocess.run(["git", "init", "--quiet", str(self.source)], check=True)
        subprocess.run(["git", "-C", str(self.source), "add", "VERSION"],
                       check=True)
        subprocess.run([
            "git", "-C", str(self.source),
            "-c", "user.email=tests@prospero-win.invalid",
            "-c", "user.name=prospero-win tests",
            "-c", "commit.gpgsign=false",
            "commit", "--quiet", "-m", "pin",
        ], check=True)
        self.commit = subprocess.run(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True).stdout.strip()
        self.manifest = self.temporary / "manifest.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.temporary)

    def write_module(self, name: str, data: bytes) -> None:
        path = self.distribution / LIBRARY / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def emit(self, *extra: str) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            VALIDATOR.main([
                "write", "--distribution", str(self.distribution),
                "--wine-source", str(self.source), "--wine-commit", self.commit,
                "--out", str(self.manifest), "--force", *extra,
            ])

    def check(self, *extra: str, manifest: Path | None = None) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            VALIDATOR.main([
                "check", "--manifest", str(manifest or self.manifest),
                "--distribution", str(self.distribution), *extra,
            ])

    def rewrite(self, mutate) -> None:
        document = json.loads(self.manifest.read_text(encoding="utf-8"))
        mutate(document)
        self.manifest.write_text(json.dumps(document), encoding="utf-8")

    def expect_failure(self, message: str, call, *arguments) -> None:
        with self.assertRaises(SystemExit) as caught:
            call(*arguments)
        self.assertIn(message, str(caught.exception))

    def test_round_trip(self) -> None:
        self.emit()
        self.check("--expect-commit", self.commit)
        document = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], VALIDATOR.SCHEMA)
        self.assertEqual(document["target"]["architecture"], "i386")
        self.assertEqual([module["name"] for module in document["modules"]],
                         ["kernel32.dll", "ntdll.dll"])
        self.assertEqual(document["wine"]["commit"], self.commit)
        self.assertEqual(document["distribution_sha256"],
                         VALIDATOR.distribution_digest(document["modules"],
                                                       document["data"]))

    def test_stages_a_data_file_and_binds_it_to_the_digest(self) -> None:
        """The NLS data is part of what the distribution is.

        A data file is recorded with its own hash and size, and the
        distribution digest covers it: a run that only listed the modules would
        call two different distributions the same one.
        """
        data = self.distribution / "nls/locale.nls"
        data.parent.mkdir(parents=True)
        data.write_bytes(b"nls-data")
        self.emit()
        with_modules = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.emit("--data", "nls/locale.nls")
        self.check()
        document = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(document["data"], [{
            "name": "nls/locale.nls",
            "path": "nls/locale.nls",
            "size": len(b"nls-data"),
            "sha256": VALIDATOR.sha256_bytes(b"nls-data"),
        }])
        self.assertNotEqual(document["distribution_sha256"],
                            with_modules["distribution_sha256"])
        # A data file that changes underneath the manifest is drift: the size
        # first, and the hash when the size is the same.
        data.write_bytes(b"different")
        self.expect_failure("size drift", self.check)
        data.write_bytes(b"nls-xxxx")
        self.expect_failure("hash drift", self.check)

    def test_refuses_to_overwrite(self) -> None:
        self.emit()
        self.expect_failure("refusing to overwrite",
                            VALIDATOR.main,
                            ["write", "--distribution", str(self.distribution),
                             "--wine-source", str(self.source),
                             "--out", str(self.manifest)])

    def test_refuses_a_dirty_wine_checkout(self) -> None:
        (self.source / "dirty").write_text("x", encoding="utf-8")
        self.expect_failure("dirty", VALIDATOR.main,
                            ["write", "--distribution", str(self.distribution),
                             "--wine-source", str(self.source),
                             "--out", str(self.manifest)])

    def test_refuses_a_wrong_wine_commit(self) -> None:
        self.expect_failure("not 0000", VALIDATOR.main,
                            ["write", "--distribution", str(self.distribution),
                             "--wine-source", str(self.source),
                             "--wine-commit", "0000000000000000000000",
                             "--out", str(self.manifest)])

    def test_refuses_a_pe64_module(self) -> None:
        self.write_module("kernelbase.dll", pe64_image("kernelbase.dll"))
        self.expect_failure("i386", VALIDATOR.main,
                            ["write", "--distribution", str(self.distribution),
                             "--wine-source", str(self.source),
                             "--out", str(self.manifest)])

    def test_missing_module(self) -> None:
        self.emit()
        (self.distribution / LIBRARY / "kernel32.dll").unlink()
        self.expect_failure("missing", self.check)

    def test_size_drift(self) -> None:
        self.emit()
        path = self.distribution / LIBRARY / "ntdll.dll"
        path.write_bytes(path.read_bytes() + b"\0")
        self.expect_failure("size drift", self.check)

    def test_hash_drift(self) -> None:
        self.emit()
        path = self.distribution / LIBRARY / "ntdll.dll"
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 0xff
        path.write_bytes(bytes(raw))
        self.expect_failure("hash drift", self.check)

    def test_machine_drift(self) -> None:
        self.emit()
        self.write_module("ntdll.dll", pe64_image("ntdll.dll"))
        self.expect_failure("machine drift", self.check)

    def test_duplicate_module_name(self) -> None:
        self.emit()
        self.rewrite(lambda document: document["modules"].append(
            dict(document["modules"][0], path=f"{LIBRARY}/copy.dll")))
        self.expect_failure("duplicate module name", self.check)

    def test_traversal_path(self) -> None:
        self.emit()
        self.rewrite(lambda document: document["modules"][0].update(
            path=f"{LIBRARY}/../../ntdll.dll"))
        self.expect_failure("traverses out of the distribution", self.check)

    def test_absolute_path(self) -> None:
        self.emit()
        self.rewrite(lambda document: document["modules"][0].update(
            path="/tmp/ntdll.dll"))
        self.expect_failure("absolute", self.check)

    def test_non_canonical_name(self) -> None:
        self.emit()
        self.rewrite(lambda document: document["modules"][0].update(
            name="NTDLL.DLL"))
        self.expect_failure("canonical", self.check)

    def test_unknown_schema(self) -> None:
        self.emit()
        self.rewrite(lambda document: document.update(schema="other/9"))
        self.expect_failure("unknown schema", self.check)

    def test_unknown_architecture(self) -> None:
        self.emit()
        self.rewrite(lambda document: document["target"].update(
            architecture="amd64"))
        self.expect_failure("unexpected architecture", self.check)

    def test_digest_mismatch(self) -> None:
        self.emit()
        self.rewrite(lambda document: document.update(distribution_sha256="0" * 64))
        self.expect_failure("distribution digest", self.check)

    def test_commit_expectation(self) -> None:
        self.emit()
        self.expect_failure("expected 0000", self.check,
                            "--expect-commit", "00000000000000000000")


if __name__ == "__main__":
    unittest.main()
