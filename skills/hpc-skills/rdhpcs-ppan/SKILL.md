---
name: rdhpcs-ppan
description: >-
  NOAA RDHPCS PPAN (Pan) post-processing and analysis cluster at GFDL in
  Princeton. Use when writing Slurm job scripts for PPAN, choosing the batch,
  stage, workflow, dask, hpetest, or gpu partition, targeting the an* analysis
  hosts or pp* post-processing hosts across mixed Xeon generations, running
  post-processing for a Gaea model run, working with the tape-backed /archive
  and CXFS /work filesystems, using /vftmp, $TMPDIR, /ptmp, /nbhome, or /net
  storage, checking quotas with homeuse, quotause, or archrpt, recalling tape
  files with dmget, or transferring files with gcp.
compatibility: Script-authoring skill; no login required. Access is through GFDL credentials and the RDHPCS bastion with CAC or YubiKey, and typically accompanies a Gaea allocation.
metadata:
  version: "1.0"
  system: ppan
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/ppan_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# PPAN — NOAA RDHPCS at GFDL

Post Processing and Analysis (PPAN), also called **Pan**, is a small cluster of
**over 130 Dell servers at the Geophysical Fluid Dynamics Laboratory (GFDL) in
Princeton, NJ**, scheduled by Slurm. About **20 analysis hosts** (`an*`) serve
interactive work and about **100 post-processing hosts** (`pp006`, `pp317`, and
so on) run batch work. PPAN supports GFDL's science community in analyzing and
interpreting models generated on other HPC systems: **Slurm lets models running
on Gaea submit post-processing jobs here**, and the cluster hosts packages
including MATLAB and the Python/R stacks.

## System Overview

PPAN carries multiple petabytes of disk plus **access to nearly 200 PB of
archive storage**. The guide's overview blurb says "Sandy Bridge to Ice Lake,
48–512 GB", but the host tables are the authority:

| Host class | Generations documented | Range per host |
|---|---|---|
| Analysis (`an*`) | `nehalem`, `westmere`, `sandybridge`, `broadwell`, `skylake`, `icelake`, `Emerald Rapids` | 8–32 CPUs, 101 GB up to **4,328 GB** (`an208`–`an212`) |
| Post-processing (`pp*`) | mixed; the table marks AVX support yes/no per host | 8–24 CPUs, **51–540 GB**, `/vftmp` 10–48 TB |

CXFS gives the analysis hosts high-performance access to `/archive` and `/work`.
Slurm is used from any analysis host, and logging in to an analysis host runs
`module load slurm` automatically.

## What PPAN Is For

- Interactive analysis on the `an*` hosts, and batch post-processing on `pp*`.
- The tail of a Gaea workflow: model output is staged, recalled from tape, and
  analyzed here rather than on the compute cluster.
- Login is `ssh` with a CAC or YubiKey. From GFDL workstations, `setup-CAC`
  enables further logins without re-authentication; YubiKey users run
  `ssh analysis`.

## Critical Requirements

- **Set `-t`** on every submission.
- **Write model output to `/work` (or archive it), never `/home`** — the home
  quota is 10 GB.
- **Choose the partition deliberately.** Post-processing hosts differ widely, from
  8-core hosts with no AVX at all to 24-core AVX hosts, and the analysis hosts run
  up through AVX-512. The guide documents partitions and per-host AVX levels,
  **not** `--constraint` values.
- **Pin module versions** in batch scripts (`module load intel/2023.2.1`). Fleet
  guidance: a silent change to a module's default version breaks reproducibility.

## Partitions

From the guide's post-processing host table:

| Partition | Nodes | Notes |
|---|---|---|
| `batch` | `pp[027-066,068,072-074]`, `pp[101,104,105]`, `pp[200-212]`, `pp[300-343]` | the workhorse set; `stage` is listed jointly as `batch/stage` |
| `workflow` | `pp[008-010]` | 16 CPUs, AVX |
| `dask` | `pp[017-026]` | 8 CPUs, no AVX |
| `hpetest` | `pp[013-014]` | 8 CPUs, no AVX |
| `gpu` | `pp[400-401]` | 24 CPUs, 540 GB, AVX |

The guide publishes **no wall-time or QOS table for PPAN** — it is a GFDL
cluster, not one of the MSU/RDHPCS compute systems. Discover the live limits
rather than assuming fleet names:

```bash
sbatch-limits          # fleet tool: limits + permitted partition/QOS combinations
sinfo                  # live partition and node state
sacctmgr show qos format=Name,MaxWall
```

PPAN also defines local queue views: `qa` (all jobs), `qi` (interactive),
`qr` (running), `qc` (completed), `qj <jobid>` (one job), `qn an|pp` (jobs on a
node class).

## Minimal Job Script

```bash
#!/bin/bash
#SBATCH --job-name=pp_post
#SBATCH --partition=batch
#SBATCH --nodes=1
#SBATCH --time=02:00:00
#SBATCH --output=/work/%u/%x-%j.log

# pp* hosts are not uniform: 8-core hosts without AVX up through 24-core AVX
# hosts. Pick the partition (see the table above) that fits the binary, and run
# `sbatch-limits` to confirm what your account may use.
module load intel/2023.2.1

cd "$SLURM_SUBMIT_DIR"
./post_process /work/$USER/forecast.out
```

Keep `-D <dir>` in mind: without it the job's working directory is the
submission directory, and if that path does not exist on the execution host,
Slurm does `cd /tmp` and runs the job there.

## Storage

| Path | Purpose | Backup | Quota command |
|---|---|---|---|
| `/home` | small persistent workspace, 10 GB quota | daily | `homeuse` |
| `/nbhome` | "no-backup" home — actually backed up weekly | weekly | `homeuse` |
| `/archive` | GFDL tape archive via CXFS, ~200 PB | tape archive | `archrpt -s` |
| `/work` | large long-term scratch | none | `quotause` |
| `/vftmp`, `$TMPDIR` | fast scratch local to each host | none | — |
| `/ptmp` | staging for FRE post-processing | none | — |
| `/net`, `/net2`, `/net3` | GFDL workstation filesystems | `/net` only | — |

Home quotas are 10 GB each: `/home` is a 10 GB area backed up daily, and
`/nbhome` is a 10 GB area backed up weekly. Check both with `homeuse` (not
`quota -vs`); `homerpt` produces a fuller report. `/vftmp` is local to every
analysis and post-processing host, and `$TMPDIR` is a per-job directory under it
that is removed when the job or session ends. `/net`, `/net2`, and `/net3` are
**not mounted on post-processing nodes** — in an analysis login session, reach
them with `gcp`. `references/storage.md` has the sizes, mount polarity, and
transfer patterns.

## Archive

`/archive` behaves like a filesystem, but the data lives on tape until it is
recalled:

```bash
dmget <files>       # recall files to disk
dmput <files>       # write files to tape
dmwho               # what is waiting on you
dmls -l             # list with status flags
dmlocate <pattern>  # search a daily-updated filename database
archrpt -s          # your archive usage
archrpt -r <group>  # group allocation report
```

Copy recalled files to `/vftmp` before heavy use. `/archive/$USER` is a symlink
into `/arch[0-8bcfgh]/$USER`, so never hard-code the target. The archive holds
**large files only** — tar or cpio small files together before archiving. There
is **no set retention policy**, so nothing expires on a schedule, but each file
exists in a single copy on tape. Archive
allocations are allocated by the GFDL director to groups, set for individuals by
group leaders, and enforced administratively rather than by a hard filesystem
limit, so check `archrpt` before a large write.

## Common Gotchas

- Assuming a uniform CPU generation across `pp*` hosts.
- Using `/home` for model output — the quota is 10 GB.
- Treating `/nbhome` as unbacked-up (it is backed up weekly), or `/vftmp` and
  `/work` as durable storage (neither is backed up, and administrators may purge
  `/vftmp/<First.Last>` when a filesystem fills).
- Skipping `archrpt` before a large archive write.
- Opening many tape-resident files without `dmget` first — each open waits on a
  recall.
- Expecting RDHPCS fleet QOS names on a GFDL cluster. Verify with
  `sbatch-limits`.
- PPAN's own Slurm notes: pointing `-o` at a *directory* schedules the job and
  then fails it immediately with `NonZeroExitCode`; output appears in the log
  file only after each line finishes, so a quiet log is not a hung job; and a
  script that does not end in a newline loses its last line.

## Additional Resources

- `references/storage.md` — filesystem sizes, mount polarity, tape workflow,
  `gcp` smartsites.
- PPAN user guide: <https://docs.rdhpcs.noaa.gov/systems/ppan_user_guide.html>
- Scheduler patterns shared across RDHPCS: see the `slurm` skill.
