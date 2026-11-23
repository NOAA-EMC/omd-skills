#!/usr/bin/env python3
"""Heuristic review gate for CMake / ecbuild test-gating and flag anti-patterns.

Scans CMake files (and optional shell/workflow helpers) for the anti-patterns
documented in references/ci-gating-antipatterns.md and
references/compiler-flags.md of the ``cmake-hpc`` skill:

* silent-test-skip -- a test registered inside ``if( EXISTS <data file> )`` or
  ``if( < pkg >_FOUND )`` whose ``else`` branch emits no ``message(WARNING ...)``
  / ``FATAL_ERROR``: in CI the test simply does not exist;
* condition-disable -- ``add_test``/``ecbuild_add_test`` carrying a ``CONDITION``
  (or sitting next to ``ENABLED OFF``), which registers nothing when false, so
  the job needs an expected test count or label baseline;
* no-enable-testing -- tests registered although the tree never calls
  ``enable_testing()`` / ``include( CTest )``. CMake configures and generates
  such a tree cleanly and ``ctest -N`` reports ``Total Tests: 0``;
* global-mutation / global-flags -- ``include_directories``,
  ``link_directories``, ``add_definitions``, ``link_libraries``, and
  ``set( CMAKE_<LANG>_FLAGS ... )``;
* glob-sources -- ``file( GLOB ... )`` feeding a source list;
* unguarded-vendor-flag -- a vendor-specific flag in a compile-options call
  outside a generator expression;
* masked-ctest / no-ctest-output / fail-fast -- ``ctest`` invoked with
  ``|| true``, without ``--output-on-failure``, or under a matrix with
  ``fail-fast: true``.

Findings are line-based heuristics: conditions assembled through variables,
functions, or macros can be misread. Exit status is 1 when a relevant finding is
reported, which is what makes it usable as a gate.

Usage:
    python3 scripts/check_cmake_antipatterns.py [PATH ...]
                                                [--format text|json]
                                                [--fail-on any|silent-test-skip|none]
                                                [--no-runners]

Stdlib only; Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DATA_EXT = ("nc", "nml", "grb", "grib2", "grb2", "h5", "hdf5", "dat", "bin",
            "tile", "restart", "csv", "txt", "yaml", "json")

IF_OPEN = re.compile(r"^\s*if\s*\(", re.I)
OTHER_OPEN = re.compile(r"^\s*(?:foreach|while)\s*\(", re.I)
ELSE_OPEN = re.compile(r"^\s*(?:else|elseif)\s*\(", re.I)
BLOCK_CLOSE = re.compile(r"^\s*(?:endif|endforeach|endwhile)\s*\(", re.I)
TEST_REG = re.compile(r"\b(?:ecbuild_add_test|add_test)\s*\(", re.I)
ENABLE_TEST = re.compile(r"\benable_testing\s*\(|\binclude\s*\(\s*CTest\b", re.I)
EXISTS_DATA = re.compile(
    r"\bEXISTS\b[^()]*?\.(?:%s)\b" % "|".join(DATA_EXT), re.I
)
FOUND_COND = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*_FOUND\b")
WARN_STMT = re.compile(r"\b(?:message\s*\(\s*(?:WARNING|SEND_ERROR|FATAL_ERROR)|ecbuild_(?:warn|error|critical))\b", re.I)
CONDITION_KW = re.compile(r"\b(?:CONDITION|ENABLED\s+OFF)\b", re.I)
GLOB_VAR = re.compile(r"\bfile\s*\(\s*GLOB(?:_RECURSE)?\s+(?:NO_FOLLOW_SYMLINKS\s+|RELATIVE\s+\S+\s+)?([A-Za-z_][A-Za-z0-9_]*)", re.I)
SOURCEISH_VAR = re.compile(r"(?:src|source|obj|test)", re.I)
GENEX = re.compile(r"\$<")
VENDOR_FLAG = re.compile(r"(?<![\w-])(?:-M[a-zA-Z]\w*|-q[a-z][\w-]*|-qsmp\w*|-h[a-z]{2,}|-ffree-line-length[\w=-]*|-fcheck=[\w,]+|-Ofast|-ffast-math|-assume\b|-r8\b)")

GLOBAL_MUTATORS = (
    (re.compile(r"^\s*include_directories\s*\(", re.I),
     "include_directories is directory-scope; use target_include_directories with PUBLIC/PRIVATE and generator expressions"),
    (re.compile(r"^\s*link_directories\s*\(", re.I),
     "link_directories hides library conflicts; use imported targets"),
    (re.compile(r"^\s*add_definitions\s*\(", re.I),
     "add_definitions is directory-scope; use target_compile_definitions"),
    (re.compile(r"^\s*link_libraries\s*\(", re.I),
     "link_libraries is directory-scope; use target_link_libraries"),
)
FLAGS_VAR = re.compile(r"^\s*set\s*\(\s*CMAKE_(?:C|CXX|Fortran|FC|CC|EXE_LINKER|SHARED_LINKER|MODULE_LINKER)_FLAGS", re.I)
COMPILE_OPTS = re.compile(r"^\s*(?:add_compile_options|target_compile_options)\s*\((.*)$", re.I)
FIND_PKG = re.compile(r"^\s*find_package\s*\(", re.I)
REQUIRED = re.compile(r"\bREQUIRED\b", re.I)

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".ompd", ".specify"}


def is_cmake_file(path: Path) -> bool:
    if path.name == "CMakeLists.txt":
        return True
    return path.suffix in {".cmake", ".cmake.in"}


def is_runner_file(path: Path) -> bool:
    return path.suffix in {".sh", ".bash", ".yml", ".yaml"} or path.name.startswith("J-")


def iter_inputs(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in paths:
        if root.is_dir():
            out.extend(sorted(p for p in root.rglob("*") if p.is_file()))
        elif root.is_file():
            out.append(root)
    return [p for p in out if not (SKIP_DIRS & set(p.parts))]


class Finding(dict):
    """A single rule hit: file, line (1-based), rule id, human message."""


def report(findings: list[Finding], rel: str, line: int, rule: str, message: str) -> None:
    findings.append(Finding(file=rel, line=line, rule=rule, message=message))


def parse_blocks(lines: list[str]) -> tuple[list[dict], list[dict]]:
    """Return (if_blocks, else_segments) by tracking block openers/closers.

    if_blocks: {"start", "end"} 0-based line indices of ``if(``/``endif``.
    else_segments: {"start", "end", "parent"} for the ``else``/``elseif`` arm of
    a block, where ``parent`` is that block's ``if`` line.
    """
    stack: list[tuple[str, int]] = []
    ifs: list[dict] = []
    elses: list[dict] = []
    pending_else: dict | None = None
    for i, ln in enumerate(lines):
        if IF_OPEN.match(ln):
            stack.append(("if", i))
            pending_else = None
        elif OTHER_OPEN.match(ln):
            stack.append(("loop", i))
        elif ELSE_OPEN.match(ln) and stack and stack[-1][0] == "if":
            if pending_else is not None:
                pending_else["end"] = i
            pending_else = {"start": i, "end": len(lines), "parent": stack[-1][1]}
            elses.append(pending_else)
        elif BLOCK_CLOSE.match(ln) and stack:
            kind, start = stack.pop()
            if kind == "if":
                ifs.append({"start": start, "end": i})
                if pending_else is not None and pending_else["parent"] == start:
                    pending_else["end"] = i
                    pending_else = None
    return ifs, elses


def enclosing(blocks: list[dict], idx: int) -> list[dict]:
    return [b for b in blocks if b["start"] < idx < b["end"]]


def call_text(lines: list[str], idx: int) -> str:
    """Text of the command invocation starting on `idx`, balanced parens."""
    depth = 0
    chunks: list[str] = []
    for j in range(idx, min(idx + 40, len(lines))):
        chunk = lines[j]
        chunks.append(chunk)
        depth += chunk.count("(") - chunk.count(")")
        if depth <= 0:
            break
    return "\n".join(chunks)


def check_cmake(path: Path, rel: str, findings: list[Finding]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    ifs, elses = parse_blocks(lines)
    tests = [i for i, ln in enumerate(lines) if TEST_REG.search(ln)]

    if tests and not ENABLE_TEST.search(text):
        report(findings, rel, tests[0] + 1, "no-enable-testing",
               "tests are registered but the tree never calls enable_testing()/include( CTest )"
               " -- CMake generates this cleanly and `ctest -N` reports Total Tests: 0")

    for i in tests:
        # gated registration
        for b in enclosing(ifs, i):
            head = "\n".join(lines[b["start"]: b["start"] + 5])
            gated = bool(EXISTS_DATA.search(head)) or bool(
                FOUND_COND.search(lines[b["start"]]) and not FIND_PKG.match(lines[b["start"]]))
            if not gated:
                continue
            arm = [e for e in elses if e["parent"] == b["start"]]
            warned = any(WARN_STMT.search(lines[j])
                         for e in arm for j in range(e["start"], min(e["end"], len(lines))))
            if not warned:
                report(findings, rel, i + 1, "silent-test-skip",
                       "test is registered inside a gated block (%s) whose else arm emits no "
                       "WARNING/FATAL_ERROR -- in CI the test silently does not exist"
                       % lines[b["start"]].strip())
        # CONDITION / ENABLED OFF on the call itself
        if CONDITION_KW.search(call_text(lines, i)):
            report(findings, rel, i + 1, "condition-disable",
                   "a false CONDITION / ENABLED OFF registers no CTest entry at all, so `ctest -N` "
                   "cannot distinguish it from a test that never existed -- assert an expected test "
                   "count or label set in the runner")

    for i, ln in enumerate(lines):
        for rx, why in GLOBAL_MUTATORS:
            if rx.match(ln):
                report(findings, rel, i + 1, "global-mutation", why)
        if FLAGS_VAR.match(ln):
            report(findings, rel, i + 1, "global-flags",
                   "CMAKE_<LANG>_FLAGS is being written from a component: put the flag in "
                   "$<$<COMPILE_LANG_AND_ID:lang,Vendor>> on the target instead")
        g = GLOB_VAR.search(ln)
        if g and SOURCEISH_VAR.search(g.group(1)):
            report(findings, rel, i + 1, "glob-sources",
                   "file( GLOB ... ) fills %s, a source/test list: new files do not trigger a "
                   "reconfigure, so an added regression test or kernel can go unbuilt" % g.group(1))
        m = COMPILE_OPTS.match(ln)
        if m and not GENEX.search(ln) and VENDOR_FLAG.search(m.group(1)):
            report(findings, rel, i + 1, "unguarded-vendor-flag",
                   "compiler-specific flag outside a generator expression -- it reaches every "
                   "toolchain that configures this tree")


def check_runner(path: Path, rel: str, findings: list[Finding]) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for i, ln in enumerate(text.splitlines()):
        low = ln.lower()
        if "ctest" not in low:
            continue
        if "|| true" in low or "||true" in low:
            report(findings, rel, i + 1, "masked-ctest",
                   "ctest result masked by `|| true` -- this job can never fail on a test")
        elif "--show-only" in low or " -n" in low:
            continue
        elif "output-on-failure" not in low:
            report(findings, rel, i + 1, "no-ctest-output",
                   "ctest runs without --output-on-failure -- a failure arrives with no diagnostic")
    if re.search(r"fail-fast:\s*true", text, re.I):
        report(findings, rel, 1, "fail-fast",
               "matrix fail-fast: true hides the remaining legs of a multi-toolchain build/test matrix")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="check_cmake_antipatterns.py",
        description="Heuristic review gate for CMake/ecbuild test-gating and flag anti-patterns.",
    )
    ap.add_argument("paths", nargs="*", default=None, type=Path,
                    help="files or directories to scan (default: .)")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--fail-on", choices=("any", "silent-test-skip", "none"), default="any",
                    help="which rules set a non-zero exit status")
    ap.add_argument("--no-runners", action="store_true",
                    help="skip shell/workflow checks for ctest invocations")
    args = ap.parse_args(argv)

    roots = list(args.paths) if args.paths else [Path.cwd()]
    findings: list[Finding] = []
    files = iter_inputs(roots)
    for f in files:
        rel = str(f)
        if is_cmake_file(f):
            check_cmake(f, rel, findings)
        elif not args.no_runners and is_runner_file(f):
            check_runner(f, rel, findings)

    if args.format == "json":
        print(json.dumps({"scanned": len(files), "findings": findings}, indent=2))
    elif findings:
        for fd in findings:
            print("%s:%s: [%s] %s" % (fd["file"], fd["line"], fd["rule"], fd["message"]))
    else:
        print("no findings across %d file(s)" % len(files))

    if args.fail_on == "none":
        return 0
    hits = [fd for fd in findings if args.fail_on == "any" or fd["rule"] == args.fail_on]
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
