"""Shared fixtures for the genesis-skills installer test suites.

Drives install.sh as a subprocess against throwaway project dirs, mirroring
`specs/001-multi-agent-installer/quickstart.md` scenarios. unittest +
subprocess keeps bash 3.2 portability honest (research R10)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO / "install.sh"


class InstallerTestCase(unittest.TestCase):
    """Base with project/catalog fixture helpers."""

    def setUp(self) -> None:
        self._tmpdirs: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self) -> None:
        for d in self._tmpdirs:
            try:
                d.cleanup()
            except OSError:
                pass

    # -- projects ----------------------------------------------------------
    def make_project(self, *, files: dict[str, str] | None = None) -> str:
        td = tempfile.TemporaryDirectory(prefix="genesis-proj-")
        self._tmpdirs.append(td)
        root = Path(td.name).resolve()
        if files:
            for rel, content in files.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
        # macOS: /var resolves under /private; canonicalize like install.sh
        return os.popen(f'cd "{root}" && pwd -P').read().strip()

    # -- tree hashing (SC-003: excludes .ompd/ and .git/) ------------------
    @staticmethod
    def tree_hash(root: str) -> str:
        import hashlib

        base = Path(root)
        rows: list[tuple[str, str]] = []
        for p in sorted(base.rglob("*")):
            rel = p.relative_to(base).as_posix()
            parts = rel.split("/")
            if parts[0] in (".ompd", ".git"):
                continue
            if p.is_dir():
                continue
            h = hashlib.sha256()
            if p.is_symlink():
                h.update(os.readlink(p).encode())
            else:
                h.update(p.read_bytes())
            rows.append((rel, h.hexdigest()))
        agg = hashlib.sha256()
        for rel, digest in rows:
            agg.update(f"{rel}\t{digest}\n".encode())
        return agg.hexdigest()

    @staticmethod
    def catalog_leaf_count() -> int:
        proc = subprocess.run(
            ["bash", str(REPO / "install.sh"), "--list"],
            capture_output=True, text=True, cwd=REPO, timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        return int(proc.stdout.splitlines()[0].split("(")[1].split(")")[0])

    # -- installer drives ---------------------------------------------------
    def run_installer(
        self,
        project: str,
        *args: str,
        stdin: str | None = None,
        env: dict[str, str] | None = None,
        install_sh: Path | None = None,
        check_rc: int | None = 0,
    ) -> subprocess.CompletedProcess[str]:
        e = dict(os.environ)
        if env:
            e.update(env)
        cmd = [
            "bash",
            str(install_sh or INSTALL_SH),
            "--project",
            project,
            *args,
        ]
        # Non-interactive is the default posture for tests (FR-015 offline,
        # no prompts); individual tests opt into the prompt flow.
        if "--no-interactive" not in args and stdin is None:
            cmd.append("--no-interactive")
        proc = subprocess.run(
            cmd,
            input=stdin if stdin is not None else "",
            capture_output=True,
            text=True,
            timeout=300,
            env=e,
        )
        if check_rc is not None:
            if proc.returncode != check_rc:
                self.fail(
                    f"install.sh rc={proc.returncode} (want {check_rc})\n"
                    f"cmd: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
                )
        return proc

    # -- catalog copy (for change/refresh/stale scenarios) ------------------
    def make_catalog_copy(self) -> Path:
        td = tempfile.TemporaryDirectory(prefix="genesis-cat-")
        self._tmpdirs.append(td)
        cat = Path(td.name).resolve()
        shutil.copy2(INSTALL_SH, cat / "install.sh")
        shutil.copytree(REPO / "tools", cat / "tools")
        shutil.copytree(REPO / "skills", cat / "skills")
        instructions = cat / ".github" / "instructions"
        instructions.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(REPO / ".github" / "instructions", instructions)
        (cat / "install.sh").chmod(0o755)
        return cat

    # -- assertions ----------------------------------------------------------
    def lock_entries(self, project: str) -> list[dict]:
        lock = Path(project) / ".ompd" / "genesis.lock"
        self.assertTrue(lock.is_file(), f"no install record at {lock}")
        return [json.loads(line) for line in lock.read_text().splitlines() if line.strip()]

    def entries_for(self, project: str, type_: str) -> list[dict]:
        return [e for e in self.lock_entries(project) if e["type"] == type_]

    def paths_in(self, project: str, type_: str) -> set[str]:
        return {e["path"] for e in self.entries_for(project, type_)}

    def summary_states(self, proc: subprocess.CompletedProcess[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for line in proc.stdout.splitlines():
            s = line.strip()
            if s.startswith(".") or "/" in s.split(" ")[0] or s.endswith(".md"):
                out[s.split(" ")[0]] = s
        return out
