# find_package Patterns for HPC Dependencies

Every dependency below is discovered once, at configure time, and then consumed
as *imported targets*. Never hand a raw `-I`/`-l` string to a target because a
module did not export a target.

## MPI

```cmake
find_package( MPI COMPONENTS C Fortran REQUIRED )
target_link_libraries( comp PRIVATE MPI::MPI_Fortran )
```

- Request exactly the components you compile with. The imported targets already
  carry the flags, so prefer `MPI::MPI_C` / `MPI::MPI_Fortran` over the
  `MPI_*_COMPILE_FLAGS` and `MPI_*_LINK_FLAGS` variables.
- On Cray (CLE), the PrgEnv wrapper *is* the MPI provider: set `ENV{CC}`/`ENV{FC}`
  to `cc`/`ftn` in the toolchain file and let `FindMPI` probe through the
  wrapper. Do not add `-lmpi` by hand — under CLE that can select the native
  rather than the Cassini library.
- Review the `MPITEST_*`/`MPI_<lang>_LIBRARY_*` cache entries `FindMPI` writes
  in any `CMakeCache.txt` diff. Mis-detected vendor flavor is the usual cause of
  a spurious `-lmpi_mpifh` appearing in a link line.

## NetCDF and PIO

```cmake
find_package( NetCDF 4.9 COMPONENTS C Fortran REQUIRED )
target_link_libraries( comp PRIVATE netCDF::netcdff netCDF::netcdf )

find_package( PIO REQUIRED )           # SCORPIO exports PIO::pio_f / PIO::pio_f90
```

- PIO/SCORPIO only behaves when NetCDF and HDF5 are consistent across the whole
  tree. Print both discovery results and fail configure if two copies of
  `libnetcdf` are reachable through the module stack: that defect shows up as
  corrupted output or a hang at scale, not as a link error.
- `find_package( HDF5 COMPONENTS C HL )` results feed PIO, ESMF, and Kokkos. One
  version, one build, per dependency path.

## ESMF

ESMF is normally consumed from an install tree that was built separately, either
through its own CMake config or the legacy `ESMF_LIBRARIES`/`ESMF_MODDIR` shape.

```cmake
find_package( ESMF 8.6 REQUIRED )      # -DESMF_DIR=/path/to/esmf at configure time
target_link_libraries( comp PRIVATE ESMF::ESMF )
```

- Match the *build mode* of the install: `ESMF_COMM=mpi`, `ESMF_OS`,
  `ESMF_COMPILER`, `ESMF_TRACEPOINT` and friends must agree with the consumer.
  A mismatch surfaces as a `.mod` version error at compile time, not as a
  configure-time failure, so record `ESMF_DIR` in the job log.
- Pin a minimum version. An install-tree ESMF upgrade that moves `lib/libg` or
  changes the module layout is a real breakage, and
  `find_package( ESMF REQUIRED )` without a version hides it.
- Do not append ESMF's own dependencies to link lines manually. If a needed
  library is missing from the exported interface, repair the imported target's
  `INTERFACE_*` properties (or the ESMF install), because every consumer
  otherwise re-implements the same workaround.

## FMS / FMS2

```cmake
find_package( FMS2 REQUIRED )          # exports fms::fms
target_link_libraries( comp PRIVATE fms::fms )
```

FMS2 manages its own module directory. A consumer that also sets
`CMAKE_Fortran_MODULE_DIRECTORY` globally can end up with two competing
`.mod` trees; keep the per-target pattern in `references/modern-targets.md`.

## Kokkos

```cmake
find_package( Kokkos REQUIRED )
target_link_libraries( comp PRIVATE Kokkos::kokkos )
```

- Device and threading configuration belongs to the Kokkos build
  (`-DKokkos_ENABLE_OPENMP=ON`, `-DKokkos_ARCH_{H100,MI300A,ZEN4}=ON`), not to
  consumer flags. A consumer that adds `-fopenmp` afterwards gets a
  runtime `Kokkos::master_threads`/backend mismatch rather than a configure
  error.
- Building Kokkos as a subproject is acceptable if the arch/thread options are
  set exactly once; `Kokkos_ENABLE_*` are dependent options, and a second
  declaration from a consumer produces a policy-conflict error at configure.
- With MPI + devices, decide explicitly who calls `MPI_Init`/`MPI_Finalize`
  (`Kokkos::ScopeGuard` vs the driver) and record the decision in a comment in
  the `CMakeLists.txt` that sets it.

## Optional dependencies

```cmake
option( COMP_WITH_GPTL "Instrument with GPTL event timers" OFF )
if( COMP_WITH_GPTL )
  find_package( GPTL REQUIRED )        # REQUIRED here: the user asked for it
  target_compile_definitions( comp PRIVATE COMP_WITH_GPTL )
endif()
```

An option that is `OFF` skips discovery; an option that is `ON` makes the
dependency `REQUIRED`. Never write `if( NOT GPTL_FOUND ) message( STATUS
"continuing without" )` — silent degradation changes what the run measures, and
in an operational suite that is indistinguishable from a wrong answer.

## Always record what was found

```cmake
message( STATUS "MPI    : ${MPI_Fortran_COMPILE_FLAGS} | ${MPI_Fortran_LINK_FLAGS}" )
message( STATUS "NetCDF : ${NETCDF_INCLUDE_DIRS} ${NETCDF_LIBRARIES}" )
message( STATUS "ESMF   : ${ESMF_DIR} (${ESMF_VERSION_STRING})" )
```

The HPC support ticket always starts with "which NetCDF did it use?" — that must
be answerable from the configure log alone, because the module stack on the
submission node can differ from the one at build time.
