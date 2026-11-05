"""Shared fixtures for the omd-skills installer test suites.

Drives install.sh as a subprocess against throwaway project dirs, mirroring
`specs/001-multi-agent-installer/quickstart.md` scenarios. unittest +
subprocess keeps bash 3.2 portability honest (research R10)."""

from __future__ import annotations

import hashlib
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
        td = tempfile.TemporaryDirectory(prefix="omd-proj-")
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
        td = tempfile.TemporaryDirectory(prefix="omd-cat-")
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
    # Installer state names. The legacy pair is what a pre-rename install left
    # behind; `seed_pre_rename_state` manufactures it so the migration path is
    # exercised with genuine installer output rather than hand-written state.
    LOCK_NAME = "omd-skills.lock"
    LEGACY_LOCK_NAME = "genesis.lock"
    MARK_BEGIN = "<!-- omd-skills:begin"
    LEGACY_MARK_BEGIN = "<!-- genesis-skills:begin"
    MARK_END = "<!-- omd-skills:end -->"
    LEGACY_MARK_END = "<!-- genesis-skills:end -->"

    def ompd(self, project: str) -> Path:
        return Path(project) / ".ompd"

    def skill_dirs(self, project: str, name: str) -> list[Path]:
        """Project directories an install placed skill `name` in."""
        return sorted({p.parent for p in Path(project).glob(f"*/skills/{name}/SKILL.md")})

    def lock_entries(self, project: str, name: str | None = None) -> list[dict]:
        """Install-record entries. With no `name`, reads whichever generation
        the project currently has, so pre-rename state can be inspected."""
        lock = self.ompd(project) / (name or self.LOCK_NAME)
        if name is None and not lock.is_file():
            lock = self.ompd(project) / self.LEGACY_LOCK_NAME
        self.assertTrue(lock.is_file(), f"no install record at {lock}")
        return [json.loads(line) for line in lock.read_text().splitlines() if line.strip()]

    MGMT_CURRENT = "<!-- managed by omd-skills install.sh;"
    MGMT_LEGACY = "<!-- managed by genesis-skills install.sh;"

    def normalize_generation(self, body: str) -> str:
        """Strip the marker-generation differences from a block body: the two
        generations differ only in the marker strings themselves."""
        return body.replace(self.MGMT_LEGACY, self.MGMT_CURRENT)

    def seed_pre_rename_state(self, project: str, *, entry_files: list[str]) -> None:
        """Install with the current script, then rename the result back to the
        pre-rename lock, staging dir and managed-block markers.

        The recorded block hashes are re-derived from the downgraded blocks, so
        the manufactured legacy state is internally consistent with itself --
        exactly what a real pre-rename install left behind.
        """
        lock = self.ompd(project) / self.LOCK_NAME
        self.assertTrue(lock.is_file(), "seed_helper needs a finished install")
        for rel in entry_files:
            p = Path(project) / rel
            text = p.read_text()
            self.assertIn(self.MARK_BEGIN, text, f"{rel}: no managed block to downgrade")
            p.write_text(
                text.replace(self.MARK_BEGIN, self.LEGACY_MARK_BEGIN)
                .replace(self.MARK_END, self.LEGACY_MARK_END)
                .replace(self.MGMT_CURRENT, self.MGMT_LEGACY)
            )
        lines = lock.read_text().splitlines()
        out: list[str] = []
        for line in lines:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("type") == "rules-block" and rec["path"] in entry_files:
                _, inner = self.block_text(project, rec["path"])
                rec["block_hash"] = "sha256:" + hashlib.sha256(inner.encode()).hexdigest()
            out.append(json.dumps(rec, separators=(",", ":")))
        lock.write_text("\n".join(out) + "\n")
        lock.rename(self.ompd(project) / self.LEGACY_LOCK_NAME)
        stage = self.ompd(project) / (self.LOCK_NAME + ".d")
        if stage.is_dir():
            stage.rename(self.ompd(project) / (self.LEGACY_LOCK_NAME + ".d"))

    def state_names(self, project: str) -> set[str]:
        d = self.ompd(project)
        return {p.name for p in d.iterdir()} if d.is_dir() else set()

    def block_text(self, project: str, name: str) -> tuple[str, str]:
        """('current'|'legacy', inner body) of the managed block in `<name>`.

        The inner body is everything between the marker LINES, mirroring
        `block_extract` in tools/installer/rules.sh, so a recorded block_hash
        can be recomputed from the file.
        """
        lines = (Path(project) / name).read_text().splitlines(keepends=True)
        for i, line in enumerate(lines):
            for gen, begin, end in (("current", self.MARK_BEGIN, self.MARK_END),
                                    ("legacy", self.LEGACY_MARK_BEGIN, self.LEGACY_MARK_END)):
                if begin in line:
                    for j in range(i + 1, len(lines)):
                        if end in lines[j]:
                            return gen, "".join(lines[i + 1:j])
                    raise AssertionError(f"{name}: unterminated managed block")
        raise AssertionError(f"{name}: no managed block")

    def marker_counts(self, project: str, name: str) -> tuple[int, int]:
        text = (Path(project) / name).read_text()
        return (text.count(self.MARK_BEGIN), text.count(self.LEGACY_MARK_BEGIN))

    def recorded_block_hash(self, project: str, name: str) -> str:
        for entry in self.lock_entries(project):
            if entry["type"] == "rules-block" and entry["path"] == name:
                return entry["block_hash"]
        raise AssertionError(f"{name}: no rules-block entry in the install record")

    def recomputed_block_hash(self, project: str, name: str) -> str:
        _, inner = self.block_text(project, name)
        return "sha256:" + hashlib.sha256(inner.encode()).hexdigest()

    def legacy_install(self, *, agents: str = "claude", mode: str = "copy",
                       domains: str = "literature-search",
                       files: dict[str, str] | None = None) -> str:
        """A project holding a genuine PRE-RENAME install.

        Runs the real installer, appends user prose after every managed block
        (prose must survive the migration), then renames the state back to the
        legacy generation. Returns the project dir; `self.legacy_args` holds
        the option list that replays the same selection.
        """
        proj = self.make_project(files=files)
        self.run_installer(proj, "--agents", agents, "--mode", mode, "--domains", domains)
        targets = sorted(self.paths_in(proj, "rules-block"))
        self.assertTrue(targets, "seed produced no managed blocks")
        for rel in targets:
            path = Path(proj) / rel
            path.write_text(path.read_text() + "\n# keep me\n")
        self.seed_pre_rename_state(proj, entry_files=targets)
        self.legacy_args = ("--agents", agents, "--mode", mode, "--domains", domains)
        return proj

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
