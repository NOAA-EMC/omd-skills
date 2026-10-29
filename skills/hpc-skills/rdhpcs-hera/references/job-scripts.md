# Hera Job Scripts Reference

Hera is an Intel Skylake Slurm system at NESCC. Every script here is complete and
copy-pasteable; replace `<account>` with your project account and `<user>` with your
`First.Last`.

The scripts abbreviate the scratch path as `/scratch3/<user>`. The real documented layout
has two more levels — `/scratch3/<portfolio>/<project>/<user>` — so use the path
`saccount_params` reports for your project rather than typing the short form.

---

## Directive Reference

| Directive | Meaning | Hera value |
|-----------|---------|-----------|
| `-A`, `--account=` | Project account | **Mandatory** on every RDHPCS job |
| `-p`, `--partition=` | Partition to run on | `hera` (default), `bigmem`, `novel`, `service` |
| `-q`, `--qos=` | Quality of service tier | `batch`, `windfall`, `debug`, `urgent`, `long`, `novel` |
| `-N`, `--nodes=` | Node count | 40 cores available per node |
| `--ntasks-per-node=` | Tasks packed on each node | `40` takes a whole regular or `bigmem` node |
| `-n`, `--ntasks=` | Total task count | Multiply by nodes you want |
| `-c`, `--cpus-per-task=` | Cores (threads) per task | `1` for pure MPI; up to 40 for OpenMP |
| `--mem=` | Memory per node when sharing | Use when you do not take the whole node |
| `-t`, `--time=` | Wall clock limit | Must fit the QOS: 8 h `batch`, 30 min `debug`, 16 h `long` |
| `-o`, `-e` | stdout / stderr paths | Write under `/scratch3`, never `/home` |
| `-J`, `--job-name=` | Job name | Appears in `squeue` and `sacct` |
| `--exclusive` | Whole nodes, no sharing | Add when you need the full 40 cores to yourself |
| `--constraint=` | Node feature filter | Generic Slurm; RDHPCS does not publish Hera node features, so ask the Help Desk before relying on it |
| `--dependency=` | Wait on another job | `afterok:12345` |
| `--array=` | Job array | `1-24%4` runs 24 members, 4 at a time |

List several partitions (`-p hera,bigmem`) so the scheduler starts the job on whichever
frees first — RDHPCS recommends this for general compute work.

---

## Serial Job

Use the `service` partition when the job needs external network or HPSS access. It
defaults to 1 core and allows at most 4.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J serial-task
#SBATCH -p service
#SBATCH -q batch
#SBATCH -N 1
#SBATCH -c 1
#SBATCH -t 1:00:00
#SBATCH -o /scratch3/<user>/serial_%j.out

cd /scratch3/<user>/run
python3 analyze.py
```

---

## MPI Job on Full Nodes

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J mpi-run
#SBATCH -p hera,bigmem
#SBATCH -q batch
#SBATCH -N 4
#SBATCH --ntasks-per-node=40
#SBATCH -t 4:00:00
#SBATCH -o /scratch3/<user>/mpi_%j.out
#SBATCH -e /scratch3/<user>/mpi_%j.err

module load intel impi

# Intel MPI does not detect Lustre by default; required for MPI-IO on scratch
export I_MPI_EXTRA_FILESYSTEM=on
export I_MPI_EXTRA_FILESYSTEM_LIST=lustre

cd /scratch3/<user>/run.456
srun ./my_mpi_app
```

Build the binary with the `mpiifort`, `mpiicc`, or `mpiicpc` wrapper from the `impi`
module — note the extra `i`, which is what selects the Intel compiler.

---

## OpenMP-Only Job

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J omp-run
#SBATCH -p hera
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH -c 40
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/<user>/omp_%j.out

module load intel

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export KMP_AFFINITY=scatter   # RDHPCS-recommended for Intel OpenMP on Hera

cd /scratch3/<user>/run
srun ./my_omp_app
```

`OMP_NUM_THREADS` must match the cores you requested. Over-subscribing a shared node
degrades performance for the other jobs on it.

---

## Hybrid MPI + OpenMP

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J hybrid-run
#SBATCH -p hera
#SBATCH -q batch
#SBATCH -N 2
#SBATCH --ntasks-per-node=8
#SBATCH -c 5
#SBATCH -t 4:00:00
#SBATCH -o /scratch3/<user>/hybrid_%j.out

module load intel impi
export OMP_NUM_THREADS=5
export KMP_AFFINITY=scatter
export I_MPI_EXTRA_FILESYSTEM=on
export I_MPI_EXTRA_FILESYSTEM_LIST=lustre

cd /scratch3/<user>/run
srun ./my_hybrid_app
```

8 tasks × 5 threads = 40 cores, one full node.

---

## Large-Memory Job

The `bigmem` partition has 268 nodes, each with 40 cores and 384 GB.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J bigmem-run
#SBATCH -p bigmem
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 8:00:00
#SBATCH -o /scratch3/<user>/big_%j.out

module load intel impi
cd /scratch3/<user>/run
srun ./my_memory_hungry_app
```

Requesting the whole node with `--ntasks-per-node=40` gives you all 384 GB, so `--mem`
is unnecessary. Specify `--mem` only when you intend to share the node.

---

## Job Array

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J ens-member
#SBATCH -p hera,bigmem
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 2:00:00
#SBATCH --array=1-24%4
#SBATCH -o /scratch3/<user>/ens_%A_%a.out

cd /scratch3/<user>/run
srun ./model_driver --member=$SLURM_ARRAY_TASK_ID
```

`%4` caps concurrency at 4 members, which keeps a 24-member ensemble from occupying the
whole queue at once. Use `%A_%a` in the output path so members do not overwrite each
other.

---

## Interactive Allocation

```bash
salloc -A <account> -p hera -q debug -N 1 -t 30:00 --ntasks-per-node=40
```

`debug` allows 30 minutes and two jobs per user, and has the highest priority — use it
to get work started quickly, not for general fast turnaround. Inside the allocation:

```bash
srun --ntasks=40 ./my_mpi_app
srun --ntasks=1 --cpus-per-task=40 ./my_omp_app
```

Packaged applications such as IDL, ImageMagick, MATLAB, and R belong on compute nodes.
IDL defaults to one thread per virtual CPU — 48 on a Hera node; set
`IDL_CPU_TPOOL_NTHREADS=1` for a serial run, and remember that IDL needing more than 10 GB
means `bigmem` or a whole node.

---

## HPSS Staging Job

Only `service` partition nodes hold the external connection, so archive traffic runs
there. Maximum 4 cores and 24 hours. Compute nodes cannot reach HPSS at all. RDHPCS's
sample staging job asks for one task, half an hour, and `windfall` so the transfer
costs nothing:

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J hpss-stage
#SBATCH -p service          # Hera and Mercury use 'service'; Gaea uses dtn_f5_f6
#SBATCH --qos windfall
#SBATCH --ntasks=1
#SBATCH --time=0:30:00
#SBATCH -o /scratch3/<user>/stage_%j.out

source $MODULESHOME/init/bash
# On a .fairmont host:
module load hpss
# On a .ncrc host instead:
#   module use /usw/hpss/modulefiles && module load hsi

cd /scratch3/<user>/staging
hpssdir=/<PORTFOLIO>/<project>/1year/<User.Id>

# Retrieve a file from HPSS -- local path first, colon, then the HPSS path
hsi "get mydata.nc : $hpssdir/mydata.nc"

# Or push a directory out, packaged as a tar (-P creates the remote directory path)
htar -P -cvf $hpssdir/results.tar ./results/
```

HPSS keeps a
single copy and overwrites targets without warning, so check the destination with
`hsi "ls -l $hpssdir"` before writing over anything, and check expiry with
`hsi "expfind -d 30 $hpssdir"`.

---

## Output and Error Conventions

| Placeholder | Expands to |
|-------------|-----------|
| `%x` | Job name (`-J`) |
| `%j` | Job ID |
| `%N` | List of allocated nodes |
| `%t` | End time in DDHHMMSS format |
| `%A` | Job array ID |
| `%a` | Array task ID |

```bash
#SBATCH -o /scratch3/<user>/%x-%j.out
#SBATCH -e /scratch3/<user>/%x-%j.err
```

Always write under `/scratch3`. `/home` carries a 30 GB quota, and job I/O there degrades
it for every user on the system.
