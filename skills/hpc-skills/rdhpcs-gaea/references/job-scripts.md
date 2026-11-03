# Gaea Job Scripts Reference

Everything here comes from the Gaea user guide
(<https://docs.rdhpcs.noaa.gov/systems/gaea_user_guide.html>). Gaea is a Slurm
federation, so every command below either names its cluster with `-M` /
`--clusters` or runs where you are standing.

## Directive Table

| Directive | Meaning on Gaea |
|-----------|-----------------|
| `-M <cluster>` / `--cluster` | Federation cluster: `c5`, `c6`, `c7`, or `es`. Defaults to the cluster of the login node you submit from. |
| `-A <projectID>` | Account; mandatory. |
| `-p <partition>` | `batch` (1–512 nodes) or `novel` (513+) on C5/C6; `eslogin_c5`, `eslogin_c6`, `dtn_f5_f6`, `cron_c5`, `cron_c6` on `es`. No C7 partitions are documented — use `scontrol --cluster c7 show partition`. |
| `-q <QOS>` / `--qos` | `normal` (default), `debug`, `urgent`, `windfall`, `dtn`, `ppan`, `hpss`. `salloc` auto-adds `interactive`. |
| `-N <nodes>` | Node count. Partition `batch` caps at 512; policy limits the largest job to 25% of system cores except on `novel`. |
| `--ntasks-per-node=<n>` | Tasks per node — 128 on C5, 192 on C6, 384 on C7. |
| `-t <time>` | Walltime; formats `minutes`, `HH:MM:SS`, `DD-HH:MM:SS`. Partition default 12:00:00, max 16:00:00; job segments are limited to 12 hours by policy. |
| `-c <ncpus>` / `--cpus-per-task` | Logical cores per task (default 1). With `--threads-per-core=1` it equals physical cores per task. Extra cores are filled within one L3 region first. |
| `--threads-per-core=<n>` | Hardware threads per core (default 1; 2 exist). **If you use `--threads-per-core=2` in `srun`, you must also set it in `sbatch`/`salloc`.** |
| `--cpu-bind=<type>` | `threads` is the default and recommended binding (`srun` form). |
| `-m block:cyclic:cyclic` | `srun` task distribution across nodes : sockets (L3 regions) : cores — the defaults. |
| `-S <cores>` | Reserve cores per node that the application cannot use (default 8). |
| `--constraint=f5` / `f6` | On `dtn_f5_f6`, choose which GPFS file system the node mounts; otherwise routing is automatic based on whether your process originated on a C5 or C6 node. |
| `-d <dep>:<jobid>` | Dependency (see below); multiple job IDs as a colon-delimited list. |
| `-J <name>` / `-o` / `-e` | Job name; output/error paths — the guide's own example uses `%x-%j.out`. |
| `--mail-type` | `BEGIN`, `END`, `FAIL`, `REQUEUE`, `INVALID_DEPEND`, `STAGE_OUT`, `ALL`, with `--mail-user`. |
| `--signal=B:USR1@300` | Signal before limit; the `B:` prefix targets the batch shell only. |
| `--reservation=<name>` | Run inside an approved reservation. |
| `-t 00:05:00` (srun) | Interactive `srun` submissions carry their own account, time, and partition. |

Job-related environment variables set for the batch script:
`SLURM_SUBMIT_DIR`, `SLURM_ACCOUNT`, `SLURM_JOBID`,
`SLURM_JOB_NUM_NODES`, `SLURM_JOB_NAME`, `SLURM_JOB_NODELIST`.

## C5 MPI Job (128 cores/node, AVX-2)

```bash
#!/bin/bash
#SBATCH -M c5
#SBATCH -A myproject
#SBATCH -J c5run
#SBATCH -p batch
#SBATCH -N 64
#SBATCH --ntasks-per-node=128
#SBATCH -t 8:00:00
#SBATCH -o %x-%j.out

module load PrgEnv-gnu
cd /gpfs/f5/${SLURM_ACCOUNT}/scratch/${USER}/run
srun ./my_app
```

## C6 MPI Job (192 cores/node, AVX-512)

```bash
#!/bin/bash
#SBATCH -M c6
#SBATCH -A myproject
#SBATCH -J c6run
#SBATCH -p batch
#SBATCH -N 16
#SBATCH --ntasks-per-node=192
#SBATCH -t 4:00:00
#SBATCH -o %x-%j.out

module load PrgEnv-gnu
cd /gpfs/f6/${SLURM_ACCOUNT}/scratch/${USER}/run
srun ./my_app
```

## C7 Job (384 cores/node)

No C7 partition names are documented. Discover first, then:

```bash
scontrol --cluster c7 show partition
```

```bash
#!/bin/bash
#SBATCH -M c7
#SBATCH -A myproject
#SBATCH -J c7run
#SBATCH -p <partition-from-scontrol>
#SBATCH -N 4
#SBATCH --ntasks-per-node=384
#SBATCH -t 4:00:00
#SBATCH -o %x-%j.out

module load PrgEnv-gnu   # C7 does not load CPE by default
cd /gpfs/f7/${SLURM_ACCOUNT}/scratch/${USER}/run
srun ./my_app
```

## Threading / Hybrid Jobs

The guide documents threading through Slurm options, not `OMP_*` variables —
it shows no `OMP_PROC_BIND`/`OMP_PLACES` examples, so prefer its own form:

```bash
srun -A <project_id> -t 00:05:00 -p <partition> -N 2 -n 4 \
     --ntasks-per-node=2 --threads-per-core=2 -c 2 ./a.out
```

Remember `--threads-per-core=2` must also appear in the `sbatch`/`salloc`
request. NUMA domains: 8 on C5 and C6, 4 on C7; 4 C5 cores share a 16 MB L3
region, 6 C6 cores share 48 MB, 16 C7 cores share 32 MB.

## Debug QOS Single-Node Job

```bash
#!/bin/bash
#SBATCH -M c6
#SBATCH -A myproject
#SBATCH -J dbg
#SBATCH -p batch
#SBATCH -q debug
#SBATCH -N 1
#SBATCH --ntasks-per-node=192
#SBATCH -t 00:30:00

module load PrgEnv-gnu
srun ./my_app
```

`debug` has the highest priority factor (1.00) and a 1-hour maximum walltime.

## Novel-Partition Job (>512 nodes)

```bash
#!/bin/bash
#SBATCH -M c6
#SBATCH -A myproject
#SBATCH -J bigrun
#SBATCH -p novel
#SBATCH -N 600
#SBATCH --ntasks-per-node=192
#SBATCH -t 8:00:00
#SBATCH -o %x-%j.out
```

`novel` is **only enabled after a system maintenance** (the 8-hour window in
which nothing else runs). If it is inactive, alert the help desk. It is the
only queue exempt from the 25%-of-cores largest-job limit.

## DTN Data-Movement Job

```bash
#!/bin/bash
#SBATCH -M es
#SBATCH -A myproject
#SBATCH -J move
#SBATCH -p dtn_f5_f6
#SBATCH -N 1
#SBATCH --constraint=f5
#SBATCH -t 2:00:00

tar cf /gpfs/f5/${SLURM_ACCOUNT}/scratch/${USER}/dump.tar ./dir
```

DTNs mount `$HOME` plus one GPFS file system: `dtn[50-79]` have F5,
`dtn[01-09]` have F6. All extensive I/O, large local copies, and every
off-Gaea transfer belong here, not on login or compute nodes.

## Interactive Allocation

```bash
salloc -M c6 -A myproject -p batch -N 1 -t 00:30:00
```

**Do not append `/bin/bash` to `salloc`** — the allocation then starts on the
login node. `salloc` adds the `interactive` QOS automatically (unless
`--qos` is given) and only one interactive job per user may run.

## Job Dependencies

| Flag | Meaning for the dependent job |
|------|-------------------------------|
| `-d after:jobid[+time]` | Start after the listed jobs start or are canceled; `+time` adds a delay in minutes. |
| `-d afterany:jobid` | Start after the listed jobs end, whatever their exit state. |
| `-d afternotok:jobid` | Start after the listed jobs fail (non-zero exit). |
| `-d afterok:jobid` | Start after the listed jobs complete successfully. |
| `-d singleton` | Serialize against your own running jobs with the same name. |

Multiple IDs take a colon-delimited list: `#SBATCH -d afterok:12345:12346`.

## Monitoring and Control

```bash
squeue -l                      # whole queue (current cluster)
squeue -l -u $USER             # your jobs
scontrol show job 12345        # detailed job info
sacct -a -X                    # all jobs, one line per allocation
sacct -u $USER                 # your jobs with individual steps
sacct -j 12345                 # steps of one job
sacct -u $USER -S 2022-07-01T13:00:00 \
      -o "jobid%5,jobname%25,nodelist%20" -X   # filtered + custom format
```

Job states: `CA` cancelled, `CD` completed, `CG` completing, `PD` pending,
`R` running. Pending reasons include `Dependency`, `JobHeldUser`,
`JobHeldAdmin`, `Priority`, `Reservation`, `AssocMaxJobsLimit`,
`ReqNodeNotAvail`, `JobLaunchFailure`, `NonZeroExitCode`.

```bash
scontrol hold 12345            # keep a queued job from starting
scontrol release 12345
scontrol update NumNodes=1000 JobID=12345
scontrol update TimeLimit=4:00:00 JobID=12345
scancel 12345                  # remove from queue
scancel -s USR1 12345          # signal instead (or -s 10)
```

Add `--clusters=c6` (or `-M c6`) to `squeue`/`sacct`/`scancel` to reach a
federation member other than the one you are on.
