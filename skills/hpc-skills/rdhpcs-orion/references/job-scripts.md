# Orion Job Scripts Reference

Orion is the Intel Skylake Slurm system at Mississippi State University's HPC2
collaboratory. Every script here is complete and copy-pasteable; replace
`<account>` with your MSU project name and `<user>` with your MSU username.

MSU's documented project layout is `/work/noaa/<project>/<user>`, so use the
directory `saccount_params` reports for your project rather than guessing the
path.

---

## Directive Reference

| Directive | Meaning | Orion value |
|-----------|---------|-------------|
| `-A`, `--account=` | Project account | **Mandatory** on every job |
| `-p`, `--partition=` | Partition to run on | `orion` (default), `bigmem`, `service` |
| `-q`, `--qos=` | Quality of service tier | `batch`, `windfall`, `debug`, `urgent`, `novel` |
| `-N`, `--nodes=` | Node count | 40 cores and 192 GB available per node |
| `--ntasks-per-node=` | Tasks packed on each node | `40` takes a whole compute or `bigmem` node |
| `-n`, `--ntasks=` | Total task count | Multiply by the nodes you want |
| `-c`, `--cpus-per-task=` | Cores (threads) per task | `1` for pure MPI; up to 40 for OpenMP |
| `--mem=` | Memory per node when sharing | Use when you do not take the whole node |
| `-t`, `--time=` | Wall clock limit | **Required in practice** — default is 5 minutes; 8 h `batch`, 30 min `debug`, 24 h `service` |
| `-o`, `-e` | stdout / stderr paths | Write under `/work/noaa/<project>`; without `-o` you get `slurm-<jobid>.out` in the submit directory |
| `-J`, `--job-name=` | Job name | Appears in `squeue`; default is the script name |
| `-D`, `--chdir=` | Working directory | `-D .` keeps a script portable; `cd $SLURM_SUBMIT_DIR` is MSU's alternative |
| `--exclusive` | Whole nodes, no sharing | MSU recommends it when a node-memory crash is involved |
| `--dependency=` | Wait on another job | `afterok:12345` |
| `--begin=` | Hold until a time | `--begin=19:25` or `--begin=now+1hour` |
| `--mail-user=` + `--mail-type=` | Email notification | **Both options are required** |
| `--export=` | Environment passing | `ALL,ndays=20` to add one variable to your environment; `NONE` to start clean |

MSU does not document `--array` or job arrays for Orion, and RDHPCS publishes no
Orion array example — do not assume array support without checking with the help
system.

---

## Wall Clock Discipline

The single most common Orion failure is a missing `-t`: the default wall clock is
**5 minutes** and the scheduler terminates the job at that point, or at the
partition limit, whichever comes first. MSU's guidance:

- Never request less than 5 minutes.
- Pad observed runtimes by 10-20% for short jobs and 5-10% for long ones.
- Over-requesting raises your wait and degrades scheduler efficiency.
- When you name several partitions, the **longest** partition limit applies, so
  size the request against the partition you may actually land on.

---

## Serial Job

A serial job gets one core's share of node memory by default. Request more with
`--mem=<MB>`, and use `service` when the job needs external network or HSMS
access (1 core maximum, 24 hours).

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J serial-run
#SBATCH -p orion
#SBATCH -q batch
#SBATCH -n 1
#SBATCH --mem=8000
#SBATCH -t 1:00:00
#SBATCH -o /work/noaa/<project>/<user>/serial_%j.out

module load contrib
cd /work/noaa/<project>/<user>/run
srun ./my_serial_app
```

---

## MPI Job on Full Nodes

MSU's own example loads the compiler and MPI modules with explicit versions and
launches with `srun -n $SLURM_NTASKS`, which keeps the script portable when the
core count changes.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J my_mpi_job
#SBATCH -p orion
#SBATCH -q batch
#SBATCH -N 4
#SBATCH --ntasks-per-node=40
#SBATCH -t 4:00:00
#SBATCH -o /work/noaa/<project>/<user>/mpi_%j.out
#SBATCH -e /work/noaa/<project>/<user>/mpi_%j.err
#SBATCH -D .

module load contrib
module load intel <version>
module load impi <version>

nt=$SLURM_NTASKS
srun -n $nt ./xhpl
```

$SLURM_NTASKS is set by Slurm from your `-N`/`--ntasks-per-node` request, so
changing the node count does not require editing the launch line.

---

## OpenMP-Only Job

Request as many cores per task as threads you want. RDHPCS publishes no Orion
specific affinity recipe, so verify the thread count the run actually gets rather
than assuming the defaults.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J omp-run
#SBATCH -p orion
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH -t 2:00:00
#SBATCH -o /work/noaa/<project>/<user>/omp_%j.out

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close

module load contrib
cd /work/noaa/<project>/<user>/run
srun ./my_omp_app
```

---

## Hybrid MPI + OpenMP

Same idea, split across tasks: pack 20 tasks per node with 2 threads each, or
whatever balance your code measures best.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J hybrid-run
#SBATCH -p orion
#SBATCH -q batch
#SBATCH -N 2
#SBATCH --ntasks-per-node=20
#SBATCH --cpus-per-task=2
#SBATCH -t 4:00:00
#SBATCH -o /work/noaa/<project>/<user>/hybrid_%j.out

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OMP_PLACES=cores
export OMP_PROC_BIND=close

module load contrib
cd /work/noaa/<project>/<user>/run
srun ./my_hybrid_app
```

---

## Large-Memory Job

The `bigmem` partition has 8 nodes with 384 GB each and accepts `batch`,
`windfall`, `debug`, and `urgent` — no `novel`.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J bigmem-run
#SBATCH -p bigmem
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=40
#SBATCH -t 4:00:00
#SBATCH -o /work/noaa/<project>/<user>/bigmem_%j.out

module load contrib
cd /work/noaa/<project>/<user>/run
srun ./my_memory_hungry_app
```

MSU's documented remedy for a job that crashes on node memory is to use more
nodes or fewer MPI tasks per node, and to add `#SBATCH --exclusive` so the node is
not shared.

---

## Interactive Allocation

MSU recommends `salloc` over `srun` for interactive work, and notes that X
windows require `ssh -X`.

```bash
salloc --x11=first -q debug -t 0:30:00 --nodes=2 -A <account>
```

Inside the allocation, run each step with `srun`. For an iterative debug loop,
MSU would rather you hold a longer interactive job in the default QOS and restart
the application inside it than repeatedly submit `debug` jobs (which are limited
to two per user).

---

## Timed and Dependent Jobs

```bash
# Hold until a time (data arrival, for example)
#SBATCH --begin=19:25
# or: #SBATCH --begin=now+1hour
```

MSU's dependency example chains two jobs with `afterok`, using `--parsable` so the
first job's ID feeds the second:

```bash
#!/bin/bash
jid1=$(sbatch --parsable -n1 -A <account> -J sim --wrap="srun sleep 10")
jid2=$(sbatch --parsable -n1 -A <account> -J post -d afterok:$jid1 --wrap="srun hostname")
```

RDHPCS also documents submitting to one QOS and telling Slurm to switch it later if
the job is still pending (via `at`). On Orion and Hercules that functionality is
**only available on login1**, and never use a delay shorter than 2 minutes
(120 seconds).

---

## `service` Partition Job (Network / HSMS)

Front-end nodes hold the external connection, so data transfer and HSMS traffic
run there. The partition allows `batch`, `windfall`, `debug`, and `urgent`, one
core, 24 hours, and `windfall` charges nothing.

```bash
#!/bin/bash
#SBATCH -A <account>
#SBATCH -J data-move
#SBATCH -p service
#SBATCH --qos=windfall
#SBATCH -n 1
#SBATCH -t 0:30:00
#SBATCH -o /work/noaa/<project>/<user>/stage_%j.out

cd /work/noaa/<project>/<user>/staging
# HSMS/HPSS traffic runs on this partition. MSU's guide does not publish an
# hsi/htar example for Orion, so load the NOAA tooling and ask the help
# system for the approved archive commands:
module load contrib noaatools
```

Do not run heavy processing on the login nodes; the login-node usage policy
applies there, and `service` jobs share those front ends.

---

## Cron

MSU documents plain `cron` on `orion-login-1` only. A crontab entry that submits
a batch job is the approved pattern; anything heavier belongs in the batch
system.

```cron
# /orion-login-1 crontab — submit, do not compute
30 4 * * * sbatch -A <account> /work/noaa/<project>/<user>/bin/daily_job.sh
```

The guide does not document `scrontab` for Orion, so check `scrontab --help`
before writing a skill or workflow that depends on it.

---

## Output and Error Conventions

RDHPCS documents `%x` (job name) and `%j` (job ID) in its batch-script example. The
rest of the table is generic Slurm — confirm with `man sbatch`, since MSU's guide
does not list them for Orion.

| Placeholder | Expands to |
|-------------|------------|
| `%x` | Job name (`-J`) — RDHPCS-documented |
| `%j` | Job ID — RDHPCS-documented |
| `%N` | Node name(s) of the allocation (generic Slurm) |
| `%t` | End time (generic Slurm) |

```bash
#SBATCH -o /work/noaa/<project>/<user>/%x-%j.out
#SBATCH -e /work/noaa/<project>/<user>/%x-%j.err
```

Omit `-e` to send stdout and stderr to the same file. If you omit `-o` too, Slurm
writes `slurm-<jobid>.out` in the directory you submitted from.

---

## Monitoring and Post-Run

```bash
squeue -u <user>              # my jobs — MSU's documented form
squeue -a                     # current jobs in the queue (RDHPCS fleet Slurm guide)
squeue --start                # point-in-time estimate of when queued jobs may start
scontrol show job <jobid>     # why a job has stayed queued (covers last 15 min)

# Jobs that ran in the last 24 hours and their states — MSU's documented form
sacct --user $USER \
  --starttime $(date --date="yesterday" +%F) \
  -X \
  --format=JobID,JobName%30,Partition,Account,AllocCPUS,State,Elapsed,QOS

shpcrpt -c orion -s           # project usage report (all projects you can see)
shpcrpt -c orion -p <project>
```

MSU notes that usernames are truncated in `squeue` output, which makes it hard to
grep — use `squeue -u <user>` instead, which also shows which jobs are active,
eligible, and blocked. `sacct` options and job states are on the `sacct` man page.

`shpcrpt` is the NOAA reporting tool exposed through `module load contrib
noaatools`; on Hercules the same command takes `-c hercules`.
