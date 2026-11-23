# ecbuild: the UFS/EMC/JEDI Build Layer

`ecbuild` (ECMWF, Apache-2.0) wraps CMake with project-level conventions and is
what `MOM6`, `CABLE`, `UFS Weather Model` components, FMS2, and most of the
JEDI/SOCA stack use. Its value is that dependencies, tests, and install
trees are handled the same way in every project — so deviations are review
findings, not style choices.

## Top-level project

```cmake
cmake_minimum_required( VERSION 3.20 )
find_package( ecbuild 3.7 REQUIRED )

project( PARTMODEL LANGUAGES C CXX Fortran VERSION 1.0.0 )

ecbuild_enable_fortran( MODULE_DIRECTORY ${CMAKE_BINARY_DIR}/module )
```

- `ecbuild_enable_fortran( MODULE_DIRECTORY <dir> )` centralises the `.mod`
  output location for every target in the tree. Pass `REQUIRED` when a Fortran
  compiler is not optional, so a mis-sourced `PrgEnv` fails configure instead of
  building a C-only subset that cannot run.
- `project()` is intercepted by ecbuild to record the version; do not re-macro
  it, and do not set `CMAKE_Fortran_MODULE_DIRECTORY` by hand on top of the
  ecbuild call (the last one silently wins per-directory and the tree ends up
  with two module paths).
- Call `ecbuild_print_summary()` at the end of the top-level
  `CMakeLists.txt`. It is the single block an operator pastes into a support
  ticket.

## Bundling dependencies

```cmake
ecbuild_bundle_initialize()

  ecbuild_bundle( PROJECT fms  GIT "https://github.com/NOAA-GFDL/FMS.git" TAG v2023.04 )
  ecbuild_bundle( PROJECT mom6 GIT "https://github.com/mom-ocean/MOM6.git" BRANCH release/convention )

ecbuild_bundle_finalize()
```

- `ecbuild_bundle( PROJECT x GIT <url> [ TAG <ref> ] )` checks the source out
  under `${PROJECT_SOURCE_DIR}/x` and then calls `add_subdirectory()` itself, so
  you do not add the subproject by hand. A missing `CMakeLists.txt` there is an
  `ecbuild_critical`, which is the point: an unpinned bundle silently builds a
  different component every week.
- Pin the revision with `TAG <tag>` or `BRANCH <branch>` — those are the
  keywords `ecbuild_bundle` forwards to `ecbuild_git`, alongside the `UPDATE`,
  `SHALLOW`, and `RECURSIVE` options. `SOURCE <path>` symlinks a local checkout
  and belongs to development only: a release tree must resolve from the file
  alone. Order the bundle by dependency direction.
- `STASH` was removed from `ecbuild_bundle` (it needs `ECBUILD_2_COMPAT`); use
  `GIT`. A subproject that sets
  `<PROJECT>_FOUND` by hand is rejected outright (recent ecbuild turns that into
  an `ecbuild_error`), because hand-rolled `_FOUND` variables break dependency
  resolution for everything downstream.
- `ecbuild_requires_macro_version( <min> )` guards against building an
  application with an older `ecbuild` than it was written for; version floors
  must be justified by the features actually used below them.

## Executables and libraries

```cmake
ecbuild_add_library( TARGET   mom6physics
                     SOURCES   src/physics.F90
                     PUBLIC_LIBS fms
                     DEPENDS   fms
                     COMPONENT model
                     NOINSTALL )

ecbuild_add_test( TARGET   test_dyn
                  SOURCES  tests/dyn_test.F90
                  LIBS     mom6dyn fms
                  DEPENDS  mom6physics
                  RESOURCES fixtures/dyn.nc
                  PROCESSORS 4
                  ENVIRONMENT OMP_NUM_THREADS=1
                  LABELS unit )
```

Keyword truth (from the `ecbuild_*` macros themselves) — an unrecognised keyword
is a hard `ecbuild_critical` error, so guessing is self-correcting:

- `ecbuild_add_executable`: `TARGET COMPONENT LINKER_LANGUAGE VERSION
  OUTPUT_NAME SOURCES SOURCES_GLOB SOURCES_EXCLUDE_REGEX OBJECTS TEMPLATES LIBS
  INCLUDES DEPENDS PERSISTENT DEFINITIONS CFLAGS CXXFLAGS FFLAGS GENERATED
  CONDITION PROPERTIES` + options `NOINSTALL AUTO_VERSION NO_AS_NEEDED`.
- `ecbuild_add_library`: as above plus `TYPE PRIVATE_LIBS PUBLIC_LIBS
  PRIVATE_INCLUDES PUBLIC_INCLUDES PRIVATE_DEFINITIONS PUBLIC_DEFINITIONS
  INSTALL_HEADERS INSTALL_HEADERS_LIST INSTALL_HEADERS_REGEX HEADER_DESTINATION
  SOVERSION`.
- `ecbuild_add_test`: `TARGET COMMAND TYPE LABELS ARGS RESOURCES TEST_DATA MPI
  OMP ENABLED LIBS INCLUDES DEFINITIONS PERSISTENT GENERATED DEPENDS
  TEST_DEPENDS TEST_REQUIRES CONDITION PROPERTIES TEST_PROPERTIES ENVIRONMENT
  WORKING_DIRECTORY CFLAGS CXXFLAGS FFLAGS LINKER_LANGUAGE` + option
  `NO_AS_NEEDED`.

Consequences worth remembering during review:

- **`RESOURCES` is copied with `execute_process( copy_if_different )` at
  configure time**, not tracked in the build graph. A missing resource file
  prints a copy error and the test is registered anyway — which is how
  configure-time file absence becomes a run-time failure. Declare the pairing in
  a comment and prefer `TEST_DATA` (which creates a `<target>_data` dependency
  and is intended for downloaded inputs) or generate the fixture inside
  `tests/CMakeLists.txt`.
- **`CONDITION` false registers nothing.** `_ecbuild_record_test()` runs only
  inside the enabled branch, so `ctest -N` does not show the test at all and CI
  cannot tell "not applicable" from "never existed". Any `CONDITION` must be
  mirrored by a visible message; never use one to hide a data dependency.
- **`MPI <n>` disables the test silently** when `MPIEXEC` is unavailable and
  `n > 1`, and `MPI 1` falls back to a sequential run. `ENABLED OFF` and
  `ECBUILD_DISABLE_MPI_TESTS` do the same. Every disable path in `ecbuild` is
  a `ecbuild_debug` line at best.
- **`OMP` defaults to 1** and adds the `openmp` label; `TYPE PYTHON` disables the
  test with an `ecbuild_warn` when no interpreter is found.

## Options

```cmake
ecbuild_add_option( FEATURE OPENMP
                    DEFAULT ON
                    DESCRIPTION "OpenMP threading"
                    REQUIRED_PACKAGES "OpenMP" )
```

Feature toggles (`ON` forces `REQUIRED_PACKAGES` and thus a configure failure,
`OFF` skips discovery) are the supported replacement for the
`if( OPTIONAL_DEP )`-then-carry-on pattern. See
`references/ci-gating-antipatterns.md`.

## Compiler and OpenMP flag helpers

Use the helpers instead of hand-maintaining `-qopenmp` vs `-fopenmp` vs `-homp`:
`ecbuild_find_omp`, `ecbuild_add_fortran_flags`,
`ecbuild_remove_fortran_flags`, and `ecbuild_purge_compiler_flags`. Their
per-vendor OpenMP flags (`GNU -fopenmp`, `Cray -homp`, `XL -qsmp=omp`,
`Intel -qopenmp`) live in the toolchain layer, not in project code. See
`references/compiler-flags.md`.
