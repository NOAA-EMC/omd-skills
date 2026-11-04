"""Tests for the cmake-hpc skill's anti-pattern checker.

The checker is a review gate, so these tests are behaviour tests: a fixture that
must be caught is caught, a fixture that is the *documented good form* (an
`else()` warning, a generator-expression flag) is not, and the shipped skill is
clean under its own rules.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "skills/omd-standards/cmake-hpc/scripts/check_cmake_antipatterns.py"

_spec = importlib.util.spec_from_file_location("check_cmake_antipatterns", SCRIPT)
assert _spec and _spec.loader
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)


def rules_of(text: str, name: str = "CMakeLists.txt") -> set[str]:
    """Run the checker's CMake rules over `text` and return the rule ids."""
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / name).write_text(text, encoding="utf-8")
        findings: list = []
        checker.check_cmake(Path(td) / name, name, findings)
        return {f["rule"] for f in findings}


def runner_rules(text: str, name: str = "run_ctest.sh") -> set[str]:
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / name).write_text(text, encoding="utf-8")
        findings: list = []
        checker.check_runner(Path(td) / name, name, findings)
        return {f["rule"] for f in findings}


GATED_NO_WARNING = """\
cmake_minimum_required(VERSION 3.23)
project( obs LANGUAGES Fortran )
enable_testing()
if( EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/data/obs.nc )
  ecbuild_add_test( TARGET obs_test SOURCES obs_test.F90 LIBS obs )
endif()
"""

GATED_WITH_WARNING = """\
cmake_minimum_required(VERSION 3.23)
project( obs LANGUAGES Fortran )
enable_testing()
if( EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/data/obs.nc )
  ecbuild_add_test( TARGET obs_test SOURCES obs_test.F90 LIBS obs )
else()
  message( WARNING "obs_test is NOT registered: data/obs.nc is missing" )
endif()
"""

FOUND_GATED = """\
cmake_minimum_required(VERSION 3.23)
project( obs LANGUAGES Fortran )
enable_testing()
find_package( NetCDF )
if( NetCDF_FOUND )
  add_test( NAME netcdf_smoke COMMAND smoke.x )
endif()
"""

CONDITION_GATED = """\
cmake_minimum_required(VERSION 3.23)
project( oops LANGUAGES Fortran CXX )
enable_testing()
ecbuild_add_test( TARGET oops_big
                  SOURCES big_test.F90
                  LIBS oops
                  CONDITION ${HAVE_LARGE_INPUT} )
"""

NO_ENABLE_TESTING = """\
cmake_minimum_required(VERSION 3.23)
project( obs LANGUAGES Fortran )
add_test( NAME smoke COMMAND smoke.x )
"""

CLEAN = """\
cmake_minimum_required(VERSION 3.23)
project( obs LANGUAGES Fortran )
enable_testing()
add_library( obs_src OBJECT obs.F90 )
target_include_directories( obs_src PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_BINARY_DIR}/mod> )
target_compile_options( obs_src PRIVATE $<$<COMPILE_LANG_AND_ID:Fortran,GNU>:-ffree-line-length-none> )
add_executable( smoke.x tests/smoke.F90 )
target_link_libraries( smoke.x PRIVATE obs_src )
add_test( NAME smoke COMMAND smoke.x )
"""

GLOBALS = """\
cmake_minimum_required(VERSION 3.23)
project( obs LANGUAGES Fortran )
include_directories( /usr/local/include )
link_directories( /usr/local/lib )
add_definitions( -DWITH_OBS )
set( CMAKE_Fortran_FLAGS "${CMAKE_Fortran_FLAGS} -O2 -ffast-math" )
add_compile_options( -qopenmp -Mfree )
file( GLOB_RECURSE MOM_SOURCES src/*.F90 )
add_library( mom ${MOM_SOURCES} )
"""


class TestTestGating(unittest.TestCase):
    def test_silent_skip_is_caught(self) -> None:
        self.assertIn("silent-test-skip", rules_of(GATED_NO_WARNING))

    def test_documented_warning_form_is_clean(self) -> None:
        self.assertEqual(rules_of(GATED_WITH_WARNING), set())

    def test_found_gated_registration_is_caught(self) -> None:
        self.assertIn("silent-test-skip", rules_of(FOUND_GATED))

    def test_condition_disable_is_caught(self) -> None:
        self.assertIn("condition-disable", rules_of(CONDITION_GATED))

    def test_missing_enable_testing_is_caught(self) -> None:
        self.assertIn("no-enable-testing", rules_of(NO_ENABLE_TESTING))


class TestFlagHygiene(unittest.TestCase):
    def test_global_mutations_and_flags_are_caught(self) -> None:
        found = rules_of(GLOBALS)
        self.assertEqual(
            found,
            {"global-mutation", "global-flags", "unguarded-vendor-flag", "glob-sources"},
        )

    def test_target_based_clean_tree_has_no_findings(self) -> None:
        self.assertEqual(rules_of(CLEAN), set())


class TestRunnerChecks(unittest.TestCase):
    def test_masked_and_silent_ctest_are_caught(self) -> None:
        self.assertEqual(
            runner_rules("ctest --test-dir build || true\nctest --test-dir build\n"),
            {"masked-ctest", "no-ctest-output"},
        )

    def test_listing_and_output_flag_are_clean(self) -> None:
        self.assertEqual(
            runner_rules(
                "ctest --test-dir build -N\n"
                "ctest --test-dir build --output-on-failure\n"
            ),
            set(),
        )

    def test_fail_fast_matrix_is_caught(self) -> None:
        self.assertIn("fail-fast", runner_rules("strategy:\n  fail-fast: true\n", "ci.yml"))


class TestCli(unittest.TestCase):
    def test_help_runs(self) -> None:
        out = subprocess.run([sys.executable, str(SCRIPT), "--help"],
                             capture_output=True, text=True, check=True)
        self.assertIn("--fail-on", out.stdout)

    def test_exit_status_tracks_findings(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "CMakeLists.txt").write_text(GATED_NO_WARNING, encoding="utf-8")
            self.assertEqual(subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True, text=True).returncode, 1)
            # the gate can be narrowed to the blocking rule only
            self.assertEqual(subprocess.run(
                [sys.executable, str(SCRIPT), "--fail-on", "none", str(root)],
                capture_output=True, text=True).returncode, 0)
            (root / "CMakeLists.txt").write_text(CLEAN, encoding="utf-8")
            self.assertEqual(subprocess.run(
                [sys.executable, str(SCRIPT), str(root)],
                capture_output=True, text=True).returncode, 0)

    def test_shipped_skill_is_clean_under_its_own_rules(self) -> None:
        rc = subprocess.run([sys.executable, str(SCRIPT),
                             str(REPO / "skills/omd-standards/cmake-hpc")],
                            capture_output=True, text=True)
        self.assertEqual(rc.returncode, 0, rc.stdout + rc.stderr)


if __name__ == "__main__":
    unittest.main()
