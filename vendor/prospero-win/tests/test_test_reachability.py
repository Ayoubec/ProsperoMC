#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Every test on disk must be built and run by the suite.

The early review found a real instance of the failure this gate exists for:
`tests/test_pw_wine_file_service.c` had a build rule but was never added to
`TESTS`, so `make test` compiled nothing and ran nothing of it while the suite
stayed green. A test that is never executed is worse than a missing one,
because it reads like coverage.

So this checks the wiring in both directions against the Makefile, which is the
single place that decides what runs:

  * every `tests/test_*.c` has a rule that builds it from it;
  * every such rule's binary is in `TESTS` (a rule for a tool is fine - the
    tools are not tests);
  * every name in `TESTS` has a rule and appears once;
  * every source a rule names exists, so a unit renamed without updating its
    rule is a failure rather than a link error nobody reaches;
  * every `tests/test_*.py` is invoked by the `test` recipe, and every Python
    suite the recipe invokes exists.

`$(CORE)` and the other make variables are not expanded here: the names inside
them come from the same Makefile, and following them would duplicate the build
system instead of checking its wiring.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RULE = re.compile(
    r"\$\(eval \$\(call test_rule,([^,]+),([^,]*),([^)]*)\)\)")
RECIPE = re.compile(r"^test: .*?\n\n", re.S | re.M)
PYTHON_SUITE = re.compile(r"python3 (tests/test_[A-Za-z0-9_]+\.py)")


def make_variable(text: str, name: str) -> str:
    """The value of `NAME := ...`, following backslash continuations."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{name} :="):
            value: list[str] = []
            while True:
                value.append(lines[index])
                if not lines[index].rstrip().endswith("\\"):
                    break
                index += 1
            return "\n".join(value)
    raise SystemExit(f"no {name} assignment found in Makefile")


def parse_makefile() -> tuple[list[tuple[str, list[str]]], list[str], str]:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    rules = [(name.strip(), sources.split())
             for name, sources, _flags in RULE.findall(text)]
    tests = make_variable(text, "TESTS").split(":=", 1)[1]
    tests = tests.replace("\\\n", " ").split()
    recipe = RECIPE.search(text)
    if recipe is None:
        raise SystemExit("no `test:` recipe found in Makefile")
    return rules, tests, recipe.group(0)


def main() -> int:
    rules, tests, recipe = parse_makefile()
    problems: list[str] = []

    rule_names = [name for name, _sources in rules]
    rule_by_name = dict(rules)
    for name in sorted({n for n in rule_names if rule_names.count(n) > 1}):
        problems.append(f"{name}: declared by more than one build rule")

    for name, sources in rules:
        for source in sources:
            if source.startswith("$"):
                continue
            if not (ROOT / source).exists():
                problems.append(f"{name}: build rule names a missing source {source}")

    # Every C test on disk must be built by some rule.
    c_tests = sorted(p.relative_to(ROOT).as_posix()
                     for p in (ROOT / "tests").glob("test_*.c"))
    builders: dict[str, list[str]] = {}
    for name, sources in rules:
        for source in sources:
            if source in c_tests:
                builders.setdefault(source, []).append(name)
    for test in c_tests:
        if test not in builders:
            problems.append(f"{test}: no build rule builds this test")

    # A rule that builds a C test must be in TESTS, or it is never executed.
    for test, names in sorted(builders.items()):
        for name in names:
            if name not in tests:
                problems.append(
                    f"{test}: built by rule {name}, which is absent from TESTS")

    # The other direction: TESTS must name real, unique rules.
    for name in sorted({t for t in tests if tests.count(t) > 1}):
        problems.append(f"{name}: listed more than once in TESTS")
    for name in tests:
        if name not in rule_by_name:
            problems.append(f"{name}: in TESTS without a build rule")

    # Python suites reach the recipe the same way the C tests reach TESTS.
    invoked = sorted(set(PYTHON_SUITE.findall(recipe)))
    for suite in invoked:
        if not (ROOT / suite).exists():
            problems.append(f"{suite}: invoked by the test recipe but missing")
    on_disk = sorted(p.relative_to(ROOT).as_posix()
                     for p in (ROOT / "tests").glob("test_*.py"))
    for suite in on_disk:
        if suite not in invoked:
            problems.append(f"{suite}: on disk but never invoked by the test recipe")

    if problems:
        raise SystemExit("test reachability failed:\n  " + "\n  ".join(problems))
    print(f"test reachability passed: {len(c_tests)} C tests built and listed, "
          f"{len(tests)} TESTS entries, {len(on_disk)} Python suites invoked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
