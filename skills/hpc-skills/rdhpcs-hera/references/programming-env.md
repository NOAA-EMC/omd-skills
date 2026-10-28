# Hera Programming Environment Reference

---

## LMOD Hierarchical Modules

Hera uses LMOD in **hierarchical** mode: `module avail` lists only what the currently
loaded tool chain exposes, so an empty result does not mean the package is missing.

```bash
module spider <pkg>          # the authoritative search — use this first
module spider <pkg> <version>
module load intel impi       # load the compiler family BEFORE the MPI module
module list                  # what is actually loaded
module purge                 # start clean when a build behaves oddly
```

The order matters. Loading `impi` without a compiler family, or with a mismatched one,
produces wrappers that fail in confusing ways at link time.

---

## Compiler and MPI Pairings

RDHPCS documents these combinations for Hera. Use the wrapper, not the bare compiler,
for MPI builds.

| Stack | Load | Fortran | C | C++ |
|-------|------|---------|---|-----|
| Intel | `module load intel impi` | `mpiifort` | `mpiicc` | `mpiicpc` |
| PGI/MVAPICH2 | `module load pgi mvapich2` | `mpif90`, `mpif77` | `mpicc` | `mpicpp` |

Note the extra `i` in the Intel MPI wrappers — `mpiifort`, not `mpifort`. That `i` is what
selects the Intel compiler backend and links the Intel MPI library.

```bash
# Typical build
mpiifort -O2 -qopenmp -o my_mpi_app my_mpi_app.f90
```

---

## MPI-IO on Lustre

Intel MPI does not detect the Lustre client on its own. Without these exports, MPI-IO
collective writes either fail or fall back to a slow path:

```bash
export I_MPI_EXTRA_FILESYSTEM=on
export I_MPI_EXTRA_FILESYSTEM_LIST=lustre
```

Put them in the job script before `srun`, not in a shell profile — the compute process
needs them, and profiles are not guaranteed to apply to the job environment.

---

## Thread Affinity

Intel OpenMP on Hera:

```bash
export KMP_AFFINITY=scatter      # RDHPCS-recommended
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
```

`scatter` spreads threads across cores before filling sockets, which is the better pattern
when several jobs share a node. `compact` is the Intel default and can leave threads
stacked on one socket while another job waits for the far cores.

Always set `OMP_NUM_THREADS` explicitly. A threaded application that ignores the
allocation and uses its default thread count oversubscribes the node and slows every other
job on it. IDL is the common offender: it defaults to one thread per virtual CPU — 48 on a
Hera compute node — so set `IDL_CPU_TPOOL_NTHREADS=1` for a serial run, or use the IDL
statement `CPU, TPOOL_NTHREADS = 1`. IDL is memory-hungry; anything over 10 GB belongs on
`bigmem` or a whole node.

---

## Profiling

Intel MPI has built-in collective statistics that need no rebuild:

```bash
export I_MPI_STATS=5                     # up to 10; higher collects more
export I_MPI_STATS_SCOPE=col             # statistics for collectives only
# csh: setenv I_MPI_STATS 5; setenv I_MPI_STATS_SCOPE col
```

Also available: Intel Trace Analyzer, which Hera builds a module called `itac` for, though
RDHPCS notes the vendor instructions for current versions may differ from what that module
assumes. Linaro Forge's MAP profiler is documented too — see Debugging below. Availability
follows the loaded compiler family, so check with `module spider <tool>`.

---

## Debugging

Linaro Forge provides the debugger (DDT) and the profiler (MAP). Both need a debug build,
and both need the compiler and MPI modules loaded alongside `forge`.

DDT attaches to an interactive allocation rather than to a batch script. The documented
sequence is:

```bash
salloc --x11=first -N 2 --ntasks=4 -A <account> -t 300 -q batch   # X11 forwarding to the first node
module load intel impi forge

# Vendor workaround needed until fixed by the vendor:
export ALLINEA_DEBUG_SRUN_ARGS="%jobid% --gres=none --mem-per-cpu=0 -I -W0 --cpu-bind=none"
# csh: setenv ALLINEA_DEBUG_SRUN_ARGS "%jobid% --gres=none --mem-per-cpu=0 -I -W0 --cpu-bind=none"

ddt srun -n 4 ./hello_mpi_c-intel-impi-debug
```

That opens the GUI on your local display. Forge remembers your session state, so
breakpoints survive to the next launch.

MAP profiling runs inside a normal batch job. Compile with the debug flag, leave the source
where it is (the paths are recorded in the binary and break if you move them), prefix the
launch command with `map --profile`, and view the results after the job ends:

```bash
module load intel impi forge
map --profile mpirun -np 8 ./myexe        # in the batch script

module load forge                          # if not already loaded
map <map_file>.map                         # graphical viewer, after the run
```

GDB works for serial code and for a single rank of an MPI job started under `salloc`. For
deadlocks and load imbalance across ranks, Forge scales better than attaching a debugger
per rank.

Intel MPI has debug-library builds that give much better tracebacks:

```bash
mpiifort -O0 -g -traceback -check all -fpe0 -link_mpi=dbg ...        # non-multithreaded
mpiifort -O0 -g -traceback -check all -fpe0 -link_mpi=dbg_mt -openmp ...  # multithreaded
export I_MPI_DEBUG=4      # startup and fabric selection detail
```

Core files are disabled by default (`ulimit -c` is zero); set the core file size to
unlimited in your shell initialization if you need them.

---

## Python

Hera provides a system Python through a module, which puts you in a conda environment:

```bash
module load rdhpcs-python
module avail python            # available versions
python3 -u script.py           # -u for unbuffered output in jobs
```

For your own packages, RDHPCS points at a Miniforge/Conda-forge install (see the
"Installing Miniforge Guide" under the Python section of the docs). Create the environment
in the project home rather than `/home`, because project home avoids purges, is easier to
share with colleagues, and behaves better from compute nodes:

```bash
conda create -p /scratch3/<portfolio>/<project>/<user>/envs/<name> python=<version> <packages>
conda config --append envs_dirs /scratch3/<portfolio>/<project>/<user>/envs
```

Three caveats RDHPCS states plainly: support staff do not have the resources to install,
debug, or maintain user packages; deactivate any activated environment before submitting a
batch job (or submit from a fresh login shell) to avoid `$PATH` problems inside the job;
and keep the Python and Conda caches trimmed. An environment on `/home` is also slow to
import from many ranks at once, so for parallel Python create it once and point jobs at it.

---

## Contrib Projects

`/contrib/<project>` is where a project keeps its own compiled software so that colleagues
and later runs can use it without rebuilding. It is managed by RDHPCS: creating or
changing a contrib area requires a help ticket.

Before building anything non-trivial, check whether the project already maintains it:

```bash
ls /contrib/<account>/
module spider <pkg>
```
