---
name: rdhpcs-hercules
description: >-
  NOAA RDHPCS Hercules at the Mississippi State University HPC2 collaboratory.
  Use when writing Slurm job scripts for Hercules, choosing the hercules or
  service partition, requesting 80-core Xeon Platinum 8380 nodes with 512 GB of
  memory, placing data on the work or work2 Lustre scratch filesystems or the
  10 GB NFS home, using MSU-HPC accounts separate from RDHPCS accounts, setting
  up cron on hercules-login-1, or discovering LMOD modules on Hercules.
compatibility: Script-authoring skill; no login required. Hercules is hosted at Mississippi State University, so access uses MSU credentials and Duo rather than the NOAA RDHPCS bastions.
metadata:
  version: "1.0"
  system: hercules
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Hercules — MSU-HPC (NOAA RDHPCS)

Hercules is the newer of the two Mississippi State University HPC2 systems that
NOAA funds. Slurm schedules the jobs, LMOD provides the software, and the
operating system is **Rocky Linux 9.x** — where Orion runs CentOS 7.x.

Access is direct: `ssh <MSU username>@hercules-login.hpc.msstate.edu` with MSU
credentials and Duo, or through the Hercules Open OnDemand portal. MSU administers
accounts and projects independently of RDHPCS. Read the `slurm` skill's *RDHPCS
Shared Policy* first for the fleet-wide QOS semantics and job-authoring rules.

Hercules and Orion share the InfiniBand fabric and the `work`/`work2` Lustre
filesystems, but MSU is explicit that they **behave as standalone systems**:
separate batch systems, separate login nodes, no federation, and FairShare
computed per system.

## System Overview

| Item | Value |
|------|-------|
| Node model | Dell EMC PowerEdge C6520 |
| CPU | Intel Xeon Platinum 8380, 40 cores x 2 sockets = **80 cores per node** at 2.30 GHz |
| Nodes | **512** |
| Total cores | 40,960 |
| Memory | **512 GB per node** — because every node is large, there are **no bigmem nodes** |
| Total system memory | 262,144 GB |
| Interconnect | Mellanox NDR-200 InfiniBand |
| Login nodes | 4 |
| Data transfer nodes | 4 |
| Development nodes | 4 |
| Scheduler / modules | Slurm / LMOD |
| OS | Rocky Linux 9.x |

Do not carry Orion's node shape into a Hercules script: Orion is 40 cores and
192 GB, Hercules is 80 cores and 512 GB.

## Critical Requirements

1. **`-A <account>` is mandatory.** Every job must name a project account.
2. **Always set `-t`.** The default wall clock is **5 minutes**; a job with no
   time request is terminated by the scheduler at 5 minutes.
3. **Never request less than 5 minutes**; MSU recommends against it, and suggests
   padding observed runtimes by 10-20% for short jobs and 5-10% for long ones.
4. **`--ntasks-per-node` goes up to 80** on Hercules, not 40.
5. **There is no `bigmem` partition.** Requesting it fails; every node already has
   512 GB.
6. Any job that passes its requested wall clock **or** its partition limit is
   terminated by the scheduler.

## Partitions

| Partition | QOS allowed | Notes |
|-----------|-------------|-------|
| `hercules` | batch, windfall, debug, urgent, novel | General compute; 80 cores and 512 GB per node |
| `service` | batch, windfall, debug, urgent | Serial jobs, maximum **1 core**, 24-hour limit, runs on front ends with external network and HSMS/HPSS access |

When you name several partitions, the **longest** partition limit governs, so size
the wall clock against the partition you may actually land on.

## QOS

MSU publishes its own per-QOS table for Orion and Hercules. It agrees with the
RDHPCS fleet policy on wall clock and billing factor, but expresses job size in
**nodes** rather than cores, and Hercules' per-QOS node ceilings are lower than
Orion's:

| QOS | Min nodes | Max nodes | Maximum Wall Clock | Billing TRES Factor | Limits |
|-----|-----------|-----------|--------------------|---------------------|--------|
| `batch` | 1 | 500 | 8 hours | 1.0 | Default QOS for projects with more than a windfall-only allocation (`RawShare=1`) |
| `urgent` | 1 | 250 | 8 hours | 2.0 | **One job per project pending or running.** FairShare drops at twice the batch rate; below 0.45 the job is changed to `batch` and the user is notified on stderr |
| `debug` | 1 | 250 | 30 minutes | 1.25 | Two jobs per user pending or running; highest priority; not for fast-turnaround general work |
| `windfall` | 1 | 250 | 8 hours, partition exception for `service` | 0.0 | Lowest priority, charges nothing, does not affect FairShare; the only QOS a windfall-only project may use |
| `novel` | 251 | largest partition | 8 hours | 1.0 | Nearly the whole system; submit a help ticket first so MSU can schedule the window with you |

Every QOS on Hercules: a maximum of **400 pending/running jobs per project**
(additional jobs are rejected), and only 20 jobs per project gain age priority.
Those caps replace the 1500-total/400-running pair RDHPCS publishes for Hera and
Ursa — do not apply the fleet numbers here.

Hercules has no `long`, `gpu`, or `gpuwf` QOS, and its size limits are node counts
rather than the core counts the fleet table gives. To read the live wall clocks:

```bash
sacctmgr show qos format=Name,MaxWall
```

## Minimal Job Script

```bash
#!/bin/bash
#SBATCH -A myproject
#SBATCH -J myjob
#SBATCH -p hercules
#SBATCH -q batch
#SBATCH -N 1
#SBATCH --ntasks-per-node=80
#SBATCH -t 4:00:00
#SBATCH -o /work/noaa/myproject/user/myjob_%j.out

module load contrib
module load intel impi
cd /work/noaa/myproject/user/run.456
srun ./my_mpi_app
```

MSU's own example writes `module load intel <version>` and `module load impi
<version>`, and on Hercules the **names and loading order of modules differ from
Orion**, so discover them with `module avail` rather than copying an Orion script.
Serial jobs get the memory-per-core share by default; request `--mem=<MB>` for
more, or `--exclusive` for the whole node. Use `service` for external network or
HSMS access.

## Storage

| Filesystem | Path | Quota | Backup | Use for |
|-----------|------|-------|--------|---------|
| Home | `/home/<userid>` | 10 GB | Nightly | Code and configs — never job I/O |
| Scratch | `/work/noaa/<project>` | project-based | **No** | Job input and output (DDN Lustre SFA18k, 9 PB shared with Orion) |
| Scratch | `/work2/noaa/<project>` | project-based | **No** | Same layout, 18 PB with an SSD "Hot Pool" that helps small files and random I/O |

Hercules has **its own home file system and its own `/apps/contrib`**, separate
from Orion's. The home file system is the **only** filesystem that is backed up.
Both `work` filesystems are scratch, not archive.

Unlike core-hour allocations, a project's **disk allocation is shared between
Orion and Hercules**, and the directory path to your data is the same on both —
so the same `/work/noaa/<project>/<user>` path works on either system, but writing
to it from both at once consumes one quota.

Only members of a NOAA project may read `/work/noaa` or `/work2/noaa`. Your home
directory is **deleted when your account is deleted**; project data is not.

MSU's published Best Practices point data that is no longer in active use back to
the R&D HPC **Niagara** system, moved with Globus because of limited network
bandwidth. Since your disk allocation is shared with Orion, that advice applies to
Hercules data too.

## Accounts and Projects

MSU accounts are completely independent of RDHPCS accounts, and **every user has
an account on both Orion and Hercules** — you still log in to each separately. A
Portfolio Manager is responsible for the projects and account managers in their
portfolio, including CPU allocations and scratch disk quotas, and requests changes
through MSU help tickets. New users change their temporary password in MSU's TAPS
within 3 days, complete MSU security and insider-threat training, and set up Duo.
Seven failed logins lock the account for 10 minutes; passwords change yearly
alongside January security training. Accounts lock after 90 days of inactivity and
are scheduled for deletion two weeks after expiry.

Your MSU username is **not** the RDHPCS `First.Last` long username. General help
goes to `rdhpcs.orion.help@noaa.gov`; role-account requests also accept
`rdhpcs.hercules.help@noaa.gov`. A shared role account is reached with
`sudo -su role-<projectname>` on login, development, and DTN nodes.

`module load contrib noaatools` exposes the NOAA tooling, including
`saccount_params`, which prints your home quota in MB plus per-project FairShare,
30-day core hours used, allocation, project directory, disk and file usage,
partition access, and available QOS list:

```bash
module load contrib noaatools
saccount_params
shpcrpt -c hercules -p <project>
```

Core-hour usage is reported **separately per system**, so `shpcrpt` takes
`-c hercules` here and `-c orion` on Orion. There is no `account_params` alias, and
the `quota -Qs` command RDHPCS documents for Hera, Ursa, Gaea and Mercury is not
documented for Hercules.

## Cron and Recurring Work

Hercules runs a **completely separate cron service** from Orion, and MSU lists its
location as "Available on `hercules-login-1` (VERIFY)" — that **(VERIFY)** marker is
literally in the published guide, so confirm the host with the help system before
scheduling anything on it. Edit your crontab on `<system>-login-1`. `scrontab` is
not documented for Hercules; `at` exists on `login1` only.

Because the two systems' schedulers are independent, **workflows must be managed
separately on each**; a cron entry on Hercules does not run anything on Orion.
Anything launched from cron must be a workflow-manager call, a script that submits
or manages batch jobs, or a data task under two minutes.

## Common Gotchas

- Carrying Orion's 40-core node shape into a Hercules script; Hercules is 80 cores.
- Requesting the `bigmem` partition, which does not exist here.
- No `-t` — the job runs only 5 minutes and is then terminated.
- Assuming the 30 GB home quota of Hera or Ursa; Hercules gives 10 GB.
- Copying an `/apps` path or module name from Orion. Hercules is spack-built into
  `/apps/spack/<package-hash>` and the hash changes whenever a package is rebuilt,
  so hard-coded paths break. Use modules.
- Expecting FairShare to carry between Orion and Hercules; each system computes its
  own, and you cannot submit to or query one system from the other.
- Writing the shared `/work` project directory from both systems at once and
  surprising your disk quota.
- Scheduling cron as if the two systems shared a crontab.
- Compiling on a login node instead of the `service` partition or a development node.
- Using an RDHPCS `First.Last` username where an MSU username is required.

## Additional Resources

- Annotated job scripts, serial and MPI patterns, interactive allocations: [references/job-scripts.md](references/job-scripts.md)
- Filesystems, quotas, backup, and the `saccount_params` report: [references/storage.md](references/storage.md)
- Module discovery, spack paths, compilers and MPI, Python, containers: [references/programming-env.md](references/programming-env.md)
- MSU-HPC user guide: https://docs.rdhpcs.noaa.gov/systems/MSU-HPC_user_guide.html
