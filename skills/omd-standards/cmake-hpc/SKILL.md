---
name: cmake-hpc
description: >
  CMake, ecbuild, and CTest for HPC and NOAA UFS-family components (MOM6, UFS
  Weather Model, CABLE, JEDI, FV3). Use when writing or reviewing
  CMakeLists.txt or .cmake modules: target-based libraries and executables,
  find_package for MPI, NetCDF, ESMF, PIO, FMS2, Kokkos, ecbuild_add_executable
  and ecbuild_add_test, Fortran module-directory isolation, GNU, IntelLLVM, and
  Cray flag hygiene, or when a test must not silently skip because a large input
  file is missing in CI.
metadata:
  version: "1.0"
  domain: standards
  as_of: "2026-02-24"
  source: https://ecmwf.github.io/ecbuild/
compatibility: >
  Authoring and review guidance for CMake 3.23+ and ecbuild 2.x. Portable across
  GNU, Intel oneAPI (ifx/icpx), and Cray PrgEnv toolchains; examples assume an
  out-of-source build on an HPC login node or CI runner.
allowed-tools: Read Grep Glob Bash(python3:*)
---

# CMake, ecbuild, and CTest for HPC

Modern, target-based build configuration for the NOAA OMD/EMC component
ecosystem, where `ecbuild` wraps CMake and the same tree must build on WCOSS,
RDHPCS machines, and CI runners with GNU, IntelLLVM, or Cray compilers.

## Which reference to load

| Task | Reference |
|---|---|
| Libraries, executables, include/module directories, linking, install/export | `references/modern-targets.md` |
| `find_package` for MPI, NetCDF, ESMF, PIO, FMS2, Kokkos; version and component handling | `references/find-packages.md` |
| `ecbuild_add_project` / `ecbuild_add_executable` / `ecbuild_add_library` / `ecbuild_add_test` | `references/ecbuild.md` |
| Compiler and linker flags for GNU, IntelLLVM (`ifx`/`icpx`), and Cray | `references/compiler-flags.md` |
| Silent test skips, `if(EXISTS ...)` gating, and CI false confidence | `references/ci-gating-antipatterns.md` |

## Core rules (apply to every change)

- **Targets carry usage requirements.** `PUBLIC` / `PRIVATE` / `INTERFACE` on
  `target_link_libraries` and `target_include_directories`, not directory-level
  `include_directories`, `link_directories`, or `add_definitions`.
- **Fortran modules live in one owned directory** per target
  (`CMAKE_Fortran_MODULE_DIRECTORY` + `$<BUILD_INTERFACE:...>` export), so two
  libraries cannot race over the same `.mod` files.
- **Every dependency is `find_package(... REQUIRED)`-checked or explicitly
  optional**, never a silent fallthrough: a missing ESMF must stop configure
  with a message naming the variable the operator has to set.
- **Flags are per-target and per-vendor** through generator expressions
  (`$<$<COMPILE_LANG_AND_ID:Fortran,GNU>:-ffree-line-length-none>`), never
  global `CMAKE_Fortran_FLAGS` string surgery.
- **A test that cannot run must fail loudly or be gated visibly.** Skipping a
  test because its input file is absent in the checkout is a silent pass; see
  `references/ci-gating-antipatterns.md` before adding any `if(EXISTS ...)`
  around `add_test` or `ecbuild_add_test`.
- **Out-of-source builds only** (`ecbuild_check_outsource`), and a project that
  pins its own `cmake_minimum_required(VERSION 3.23)` at the top of
  `CMakeLists.txt`.

## Gate check

`scripts/check_cmake_antipatterns.py` flags the specific anti-patterns this
skill forbids (silent `if(EXISTS)` test gating, global flag and directory
commands, un-`REQUIRED` `find_package`, non-generator vendor flags). Run it from
the skill root against any CMake tree:

```bash
python3 scripts/check_cmake_antipatterns.py /path/to/project
```
