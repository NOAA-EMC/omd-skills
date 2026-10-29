# Ursa Job Scripts Reference

Ursa is the AMD Genoa CPU and GPU system at NESCC, sharing its file systems with Hera.
Every script here is complete and copy-pasteable; replace `<account>` with your project
account and `<user>` with your `First.Last`.

Scratch paths are written in the short `/scratch3/<user>` form. The documented layout is
`/scratch[3,4]/<portfolio>/<project>/<user>`, so list `/scratch3/` to find your portfolio and
project directory names rather than guessing at the short form. `saccount_params`, which prints
those paths on Hera, is not available on Ursa.

---

## Directive Reference

| Directive | Meaning | Ursa value |
|-----------|---------|-----------|
| `-A`, `--account=` | Project account | **Mandatory** on every RDHPCS job |
| `-p`, `--partition=` | Partition to run on | `u1-compute` (default), `u1-service`, `u1-h100`, `u1-gh`, `u1-mi300x` |
| `-q`, `--qos=` | Quality of service tier | `batch`, `windfall`, `debug`, `urgent`, `long`; `gpu` or `gpuwf` on GPU partitions |
| `-N`, `--nodes=` | Node count | 192 threads per node on `u1-compute` and `u1-h100` |
| `--ntasks-per-node=` | Tasks packed on each node | `192` takes a whole CPU node; `4` is a reasonable H100 split |
| `-n`, `--ntasks=` | Total task count | Multiply by nodes you want |
| `-c`, `--cpus-per-task=` | Cores (threads) per task | `1` for pure MPI; up to 48 with 3 H100s; 96 for one GH200 |
| `--gpus=` | GPU request | `<type>:<count>` — `h100`, `gh200`, `mi300x` |
| `--mem=` | Memory per node when sharing | 2 GB per core available; use when you do not take the whole node |
| `--exclusive` | Whole nodes, no sharing | **Load-bearing** — sharing is enabled for all job sizes since 2026-06-18 |
| `-t`, `--time=` | Wall clock limit | Must fit the QOS: 8 h `batch`, 30 min `debug`, 16 h `long`, 168 h `gpu`, 48 h `gpuwf` |
| `-o`, `-e` | stdout / stderr paths | Write under `/scratch3`, never `/home` |
| `-J`, `--job-name=` | Job name | Appears in `squeue` and `sacct` |
| `--dependency=` | Wait on another job | `afterok:12345` |
| `--array=` | Job array | `1-24%4` runs 24 members, 4 at a time |

`u1-service` is capped at 64 cores and/or 250 GB of memory per user with a 24 hour wall
limit, and it is where compilation and HPSS or external-network work belongs.

Ursa modules come from a spack tree. The Ursa page names the available compilers (Intel
oneAPI, NVIDIA nvhpc, AMD AOCC) and MPIs (Intel MPI, HPC-X, OpenMPI) but publishes no
`module load` examples. The fleet compilers page gives `intel/<version>`, `impi/<version>`
and `nvhpc/<version>`, so use those shapes and confirm the AOCC, HPC-X, OpenMPI and ROCm
strings with `module spider`.

---

## CPU MPI Full-Node Job

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J cpu-mpi
#SBATCH -p u1-compute
#SBATCH -q batch
#SBATCH -N 2
#SBATCH --ntasks-per-node=192
#SBATCH -c 1
#SBATCH --exclusive
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/<user>/cpu_mpi_%j.out
#SBATCH -e /scratch3/<user>/cpu_mpi_%j.err

cd /scratch3/<user>/run.456

module load intel impi
export I_MPI_EXTRA_FILESYSTEM=on
export I_MPI_EXTRA_FILESYSTEM_LIST=lustre

srun ./my_mpi_app
```

One task per thread with `-c 1` is the pure-MPI pattern on 192-thread Genoa nodes. Drop
`--exclusive` and add `--mem=` if the run is small enough to share a node.

---

## CPU OpenMP-Only Job

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J omp
#SBATCH -p u1-compute
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH -t 4:00:00
#SBATCH -o /scratch3/<user>/omp_%j.out

cd /scratch3/<user>/run
module load intel

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export KMP_AFFINITY=scatter

srun ./my_omp_app
```

`OMP_NUM_THREADS` must match the cores you requested. A threaded run that uses its default
thread count oversubscribes the node and slows every other job sharing it, which matters more
than ever now that sharing is on for all job sizes.

---

## Single-GPU H100 Job

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J gpu1
#SBATCH -p u1-h100
#SBATCH -q gpu
#SBATCH -N 1
#SBATCH --gpus=h100:1
#SBATCH --ntasks=1
#SBATCH -c 48
#SBATCH -t 4:00:00
#SBATCH -o /scratch3/<user>/gpu1_%j.out

module load nvhpc
srun --cpu-bind=cores ./my_gpu_app
```

## Multi-GPU H100 Job

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J gpu2
#SBATCH -p u1-h100
#SBATCH -q gpu
#SBATCH -N 1
#SBATCH --gpus=h100:2
#SBATCH --ntasks-per-node=2
#SBATCH -c 96
#SBATCH --exclusive
#SBATCH -t 8:00:00
#SBATCH -o /scratch3/<user>/gpu2_%j.out

module load nvhpc
srun --cpu-bind=cores ./my_gpu_app
```

Each `u1-h100` node has 2 H100s with 94 GB each and 192 AMD cores, so a two-GPU job can take
the whole node. The documented priority-access form is a non-interactive submit:

```bash
sbatch -A mygpu_project -p u1-h100 -q gpu --gpus=h100:3 my_ml.job
```

Three GPUs means two nodes, which is exactly why `gpu` projects are worth requesting rather
than hand-counting.

---

## H100 at Windfall Priority

For a project with a CPU allocation but no `gpu-` allocation, use `gpuwf`:

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J gpu-windfall
#SBATCH -p u1-h100
#SBATCH -q gpuwf
#SBATCH -N 1
#SBATCH --gpus=h100:2
#SBATCH -t 12:00:00
#SBATCH -o /scratch3/<user>/gpuwf_%j.out

module load nvhpc
srun ./my_gpu_app
```

`gpuwf` costs nothing and does not lower your FairShare, but it is the lowest GPU priority,
is capped at 10 GPUs per project, and stops scheduling your queued jobs once your running
jobs exceed 192 gpu-hours (`gpu_allocated * wallclock_requested`). Keep the walltime honest:
a long request inflates that product and blocks your own queue.

---

## GH200 Interactive Session

The exploratory partitions are documented as interactive allocations — get the node, then
compile and run on it:

```bash
salloc -A <account> -t 480 -p u1-gh -q gpuwf --gpus=gh200:1
module load nvhpc
# build here, on the node
srun ./my_app
```

The GH200 CPU is an **ARM Grace with 72 cores and about 213 GB**, not the x86 Genoa used
elsewhere on Ursa. Binaries built for `u1-compute` or `u1-h100` will not run here; rebuild.
One GH200 gpu-hour bills as 72 core-hours.

---

## MI300X Job

```bash
salloc -A <account> -t 480 -p u1-mi300x -q gpuwf --gpus=mi300x:2
module load rocm          # confirm the name with module spider
srun ./my_app
```

Each of the 5 MI300X nodes has 96 **Intel** cores and 8 AMD MI300X APUs with 192 GB each, and
takes ROCm rather than CUDA. One MI300X gpu-hour bills as 96/8 = 12 core-hours.

---

## u1-service Serial Job

Use this for HPSS traffic, database access, downloads, and builds. External network access
exists only on these nodes.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J stage
#SBATCH -p u1-service
#SBATCH -q windfall
#SBATCH --ntasks=1
#SBATCH -c 1
#SBATCH --time=0:30:00
#SBATCH -o /scratch3/<user>/stage_%j.out

source $MODULESHOME/init/bash
module load hpss          # not loaded by default

cd /scratch3/<user>/staging
hpssdir=/<PORTFOLIO>/<project>/1year/<User.Id>

# Local path first, colon, then the HPSS path -- this is not FTP order
hsi "get mydata.nc : $hpssdir/mydata.nc"
htar -P -cvf $hpssdir/results.tar ./results/
```

Maximum 64 cores and/or 250 GB per user, and 24 hours. `u1-service` allows only `batch` and
`windfall`. HPSS keeps a single copy and overwrites targets without warning, so list the
destination with `hsi "ls -l $hpssdir"` before writing over anything.

---

## Job Array

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J ens
#SBATCH -p u1-compute
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=192
#SBATCH --array=1-24%4
#SBATCH -t 2:00:00
#SBATCH -o /scratch3/<user>/ens_%A_%a.out

cd /scratch3/<user>/run
module load intel impi

member=/scratch3/<user>/inputs/member.$SLURM_ARRAY_TASK_ID
srun ./my_mpi_app "$member"
```

`%4` caps concurrent members at 4. Without the cap, all 24 members enter the queue at once
and compete for the same node.

---

## QOS Escalation

Start cheap and promote only if the job will not start — RDHPCS recommends this to protect
FairShare:

```bash
sbatch --qos=windfall job.sh                  # submit at no cost
scontrol update job 26866,26867 qos=batch     # promote now
echo "scontrol update job 26990 qos=batch" | at -M now +5min   # promote if still pending
```

Never schedule an `at` time below 120 seconds. A job moved to a QOS it does not qualify for
stays pending forever rather than failing. For GPU jobs the same trick promotes `gpuwf` to
`gpu`, and only works if the project actually holds a `gpu-` allocation of 2 or larger.

---

## Output and Error Conventions

| Placeholder | Expands to |
|-------------|-----------|
| `%x` | Job name (`-J`) |
| `%j` | Job ID |
| `%N` | List of allocated nodes |
| `%A` | Job array ID |
| `%a` | Array task ID |

```bash
#SBATCH -o /scratch3/<user>/%x-%j.out
#SBATCH -e /scratch3/<user>/%x-%j.err
```

Always write under scratch. `/home` carries a 30 GB quota, and job I/O there degrades it for
every user on the system.
