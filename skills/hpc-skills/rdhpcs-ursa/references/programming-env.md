# Ursa Programming Environment Reference

Ursa's software is installed with **spack**, and the module layout is like the MSU systems.
That has one practical consequence: module names carry versions and are not always guessable,
so discovery comes before any build command you copy from elsewhere.

---

## Module Discovery

```bash
module spider <pkg>              # the entry point — finds everything, including hidden packages
module spider intel impi         # the recommended stack, with available versions
module load intel/<version> impi/<version>
module list                      # what is actually loaded
module purge                     # start clean when a build behaves oddly
```

`module avail` lists only what the loaded tool chain exposes, so an empty result does not mean
the package is missing. Load a compiler family before the MPI module; wrappers built against a
mismatched family fail at link time in confusing ways.

---

## Compilers

| Compiler | Load | Serial commands | Notes |
|----------|------|-----------------|-------|
| Intel oneAPI | `module load intel/<version>` | `ifx`/`ifort` (Fortran), `icx`/`icc` (C/C++) | The fleet compilers page lists Intel and NVIDIA as the available compilers and **recommends Intel with Intel MPI** unless there is a specific reason not to |
| NVIDIA HPC | `module load nvhpc/<version>` | `nvfortran`, `nvc`, `nvc++`, `nvcc` for CUDA C | CUDA targets `u1-h100` and `u1-gh` |
| AMD AOCC | confirm with `module spider` | — | The Ursa guide lists AOCC; the fleet compilers page does not, so verify the module name before relying on it |

Recommended Intel optimization starting points from the docs:

```bash
-O3 -xHOST -ip -align array64byte
-O3 -qopt-zmm-usage=high -axCORE-AVX512 -align array64byte -ip   # Skylake (Hera)
```

`-xHOST` is recommended for **Hera** users only. On Ursa, build on a Ursa node so the
instruction set matches Genoa. AVX-512 may or may not help — the docs advise testing with and
without. For results that must be identical across core counts, use `-fp-model strict` or
`-fp-model precise`, accepting a performance cost.

Debug builds:

```bash
-O0 -g -traceback -check all -fpe0
```

---

## MPI

| MPI | Load | Documented guidance |
|-----|------|---------------------|
| Intel MPI | `impi/<version>` | The fleet recommendation is Intel compiler plus Intel MPI |
| HPC-X (NVIDIA) | confirm with `module spider` | On **Ursa specifically**, RDHPCS measured much better performance and stability than Intel MPI on communication-intensive benchmarks, because HPC-X is optimized for the NDR-200 fabric |
| OpenMPI | confirm with `module spider` | Available through spack |

The two recommendations are not contradictory — the general page states the Intel pairing,
while the Ursa page steers this system's GPU and communication-intensive work to HPC-X. If
your code is MPI-heavy on Ursa, try HPC-X first.

Intel MPI wrappers carry an extra `i`: `mpiifort`, `mpiicc`, `mpiicpc`, and the newer
`mpiifx -fc=ifx` and `mpiicx`.

MPI-IO on the Lustre file systems needs the extra-filesystem exports; Intel MPI does not detect
Lustre by default. RDHPCS documents this on the **Hera** page, and Ursa runs on the same
`/scratch[3,4]` Lustre file systems, so apply it here too:

```bash
export I_MPI_EXTRA_FILESYSTEM=on
export I_MPI_EXTRA_FILESYSTEM_LIST=lustre
```

Put them in the job script before `srun`, not in a shell profile — the compute process needs
them, and profiles are not guaranteed to apply to the job environment.

---

## Accelerator Selection

| Partition | Vendor stack | CPU |
|-----------|--------------|-----|
| `u1-h100` | CUDA (`nvhpc`) | 192 AMD Genoa cores |
| `u1-gh` | CUDA (`nvhpc`) | **ARM Grace, 72 cores** |
| `u1-mi300x` | **ROCm** | 96 Intel cores |

The `u1-gh` nodes are ARM. A binary built for `u1-compute` or `u1-h100` will not run there —
rebuild on the node, which is why the documented exploratory workflow is an interactive
`salloc` followed by compiling and running inside the allocation.

RDHPCS does not publish GPU-aware MPI settings for Ursa. If you need them, follow the vendor
documentation for the HPC-X or OpenMPI build that `module spider` shows you, and verify with a
small test before a long run.

---

## CPU Binding and Affinity

The advanced Slurm usage page (fleet-wide) documents a clean one-process-per-physical-core
combination:

```bash
srun --exclusive --hint=nomultithread -n1 --cpus-per-task=1 --cpu-bind=cores ./probe
```

| Flag | Purpose |
|------|---------|
| `-n1` | One task per step |
| `--cpus-per-task=1` | Reserve exactly one CPU per task |
| `--exclusive` | No other step may share this CPU |
| `--hint=nomultithread` | Avoid sibling hyperthread collisions |
| `--cpu-bind=cores` | Pin the task to its assigned core |

Add `--cpu-bind=verbose` and read its output to detect genuine core collisions when several
steps run in parallel. This matters more on Ursa than on most systems because node sharing is
enabled for **all job sizes** as of 2026-06-18: without `--exclusive`, your tasks can land on
sibling threads of a core another project is using.

For Intel OpenMP, the Hera guide recommends `KMP_AFFINITY=scatter` for best performance with
most OpenMP applications; RDHPCS publishes no Ursa-specific affinity guidance, so treat the
Intel recommendation as the starting point and always set `OMP_NUM_THREADS` to the cores you
requested.

---

## Debugging

Linaro Forge DDT is the documented graphical debugger across RDHPCS: single process,
multithreaded, MPI, OpenMP, and hybrids such as MPI plus OpenMP or MPI plus CUDA. It supports
C, C++, Fortran derivatives, and limited Python.

Because DDT is graphical, running it over a wide-area network is slow. The documented approach
is a **remote connection**: install Linaro Forge locally, open an SSH connection with a local
port forward to the RDHPCS system, then configure DDT's Remote Launch to use that forward. The
local client version must match the Forge version on the system, which sometimes means
installing an older Forge release.

The Hera page shows the in-allocation form of the same idea, which works wherever Forge is
available:

```bash
salloc --x11=first -N 2 --ntasks=4 -A <account> -t 300 -q batch
module load intel impi forge
ddt srun -n 4 ./hello_mpi_c-intel-impi-debug
```

Ursa's own guide does not document a DDT invocation, and GDB, GDB4HPC and Valgrind4hpc are
documented for **Gaea** rather than Ursa. Use `module spider forge` to see what is installed,
and do not assume a Gaea tool exists here.

---

## Profiling

Nothing on the Ursa page documents a profiler, so treat these as fleet-level pointers rather
than Ursa guarantees:

- Intel MPI collective statistics need no rebuild — `I_MPI_STATS` up to 10, with
  `I_MPI_STATS_SCOPE=col` for collectives only.
- Linaro Forge MAP profiling runs by prefixing the launch command with `map --profile` inside a
  normal batch job, then opening the resulting `.map` file with `map <file>.map`. Compile with
  debug flags and do not move the sources, because the paths are recorded in the binary.
- TAU is documented on Hera.
- The HPE Performance Analysis Tools are documented on **Gaea** only.

Check `module spider` for what is actually installed on Ursa before building a workflow around
any of them.

---

## Python

Load the system module first:

```bash
module load rdhpcs-python
module avail python
python3 -u script.py           # -u for unbuffered output in jobs
```

For your own packages, RDHPCS documents a Miniforge/Conda-forge install. Create environments in
the project home rather than `/home`: project home avoids purges, is easier to share, and
behaves better from compute nodes.

```bash
conda create -p /scratch3/<portfolio>/<project>/<user>/envs/<name> python=<version> <packages>
conda config --append envs_dirs /scratch3/<portfolio>/<project>/<user>/envs
```

Three documented caveats: support staff do not have the resources to install, debug, or
maintain user packages; deactivate any activated environment before submitting a batch job (or
submit from a fresh login shell) to avoid `$PATH` problems inside the job; and keep the Python
and Conda caches trimmed.

---

## Containers

RDHPCS supports **SingularityCE and Apptainer**, not Docker. The documented reason is that
Docker normally needs root or sudo to build and run, which is not acceptable on shared HPC
systems, and its microservice model does not fit large parallel jobs.

Ursa runs **apptainer**, and no module load is required:

| System | Software | Module |
|--------|----------|--------|
| Ursa | apptainer | none required |
| Hera | singularity, apptainer | none required |
| Gaea | apptainer | none required |
| PPAN | singularity | none required |
| Hercules/Orion | singularity | `module load singularity` |

Convert a Docker or OCI image to a `.sif`:

```bash
singularity pull image.sif docker://rockylinux:9
singularity pull rocky9-gnu13-ompi416.sif docker://noaaepic/rocky9-gnu:13.3.1-ompi416
singularity build image.sif docker://rockylinux:9      # build adds options
```

`pull` is a simple conversion; `build` is more general. Both produce a `.sif`, and neither
produces a bit-for-bit identical image. NOAA-EPIC publishes prepared images for the supported
Rocky Linux base.

**Ursa-specific:** pulling or building a container may need a service node with extra memory, so
allocate one first:

```bash
salloc -N 1 -p u1-service -A <project> -t 30:00 --mem=16G
```

MPI inside containers follows three documented models — hybrid (host MPI plus container MPI),
host MPI only with bind mounts, and fully containerized. Bind mounts are how the container
reaches `/scratch3`; the container has its own filesystem and relies on the host for storage,
hardware, and the interconnect.

**The `u1-gh` Grace Hopper compute nodes are air-gapped.** You cannot build or pull an image on
them. Build or pull on a **login node** and target the ARM architecture explicitly, then use
the resulting `.sif` from the allocation:

```bash
singularity build --arch arm64 container_arm.sif container.def
singularity pull --arch arm64 container_arm.sif <container_uri>
```

RDHPCS runs a container registry at `https://registry.rdhpcs.noaa.gov`. Where Apptainer is
installed you may build images and push them there, and the same registry can be used as a
**spack mirror**.

---

## Contrib Projects

`/contrib/<project>` is where a project keeps its own compiled software so colleagues and later
runs can use it without rebuilding. It is managed by RDHPCS: creating or changing a contrib
area requires a help ticket.

Before building anything non-trivial, check whether the project already maintains it:

```bash
ls /contrib/<account>/
module spider <pkg>
```
