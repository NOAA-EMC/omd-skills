# Hera Storage Reference

Hera's file systems are shared with Ursa at NESCC. Two of them are backed up and one of
those is small; the rest are scratch, which means nothing in them survives a decision to
stop paying for it.

Scratch directories have a portfolio level in them. The documented layout is
`/scratch[3,4]/<portfolio>/<project>/<user>`, so expect paths like
`/scratch3/noaa-hpc/myproject/First.Last` rather than a project directory directly under
`/scratch3`.

---

## Filesystem Overview

| Filesystem | Path | Quota | Backed up | Purged | Use for |
|-----------|------|-------|-----------|--------|---------|
| Home | `/home/First.Last` | 30 GB | Yes, plus `~/.snapshot` | No | Code, configs, small persistent files |
| Home snapshots | `/home/First.Last/.snapshot/` | counts toward home | Per-day copies | Rolling | Recovery of deleted or corrupted files |
| Scratch | `/scratch3`, `/scratch4` | project-based | **No** | No (except `stmp`) | Job input and output |
| Scratch temp | `/scratch[3,4]/.../stmp` | project-based | **No** | Weekly, Monday, >30 days | Short-lived intermediates |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public` | **No** | No | All-flash experimental work |
| VAST purged | `/scratch5/purged/First.Last` | 250 TB pool | **No** | Files not accessed in 90 days | Everyone else's `/scratch5` access |
| Archive | NESCC-HPSS | portfolio-managed | **No — single copy** | Yes, on retention expiry | Long-term retention |

---

## Checking Quota and Recovering Files

```bash
# Projects, fairshare, partition access, and disk and file usage per project directory
saccount_params

# Home usage against the quota
quota -Qs

# Where the bytes actually are
du -sh /scratch3/<portfolio>/<project>/<user>/*
```

`saccount_params` is documented on Hera and Orion only — it is not available on the rest of
the fleet. It prints home quota in MB, your fairshare and rank per project, the partitions
and QOSes you may use, and a `DiskInUse`/`Quota`/`Files`/`FileQUota` line for each project
directory. The `-l` option adds 30-day core-hour usage and allocation.

Quota problems on RDHPCS are usually file *count* rather than bytes: a directory of a
million small results can exhaust an inode quota while `du` reports gigabytes. Compare
`Files` against `FileQUota` before hunting for large files.

`/home` keeps per-day snapshots in a directory that does not appear in `ls`, even `ls -a`,
but which you can list directly. Scratch has **no** snapshots — a file deleted from
`/scratch3` is gone:

```bash
ls /home/$USER/.snapshot/          # entries look like 2026-03-09_0015-0600.daily
cp /home/$USER/.snapshot/<daily-snapshot-name>/important.f90 .
```

The snapshot directory is available in any subdirectory of `/home`, so recover a file from
wherever you are. Hourly copies appear alongside the daily ones as `hourly.YYYY-MM-DD-HHMM`.

---

## Purge Policy

| Location | Rule |
|----------|------|
| `stmp` on `/scratch3-4` | Purged weekly on Mondays for files older than 30 days |
| `/scratch5/purged` | Purged for files not accessed in 90 days |
| `/scratch3`, `/scratch4` outside `stmp` | Not purged — but never backed up |
| Node-local temp | RDHPCS documents `$TMPDIR` only for PPAN, so use a scratch `stmp` directory for intermediates |

Find files approaching the `stmp` threshold before they disappear:

```bash
find /scratch3/<portfolio>/<project>/<user>/stmp -type f -atime +25
```

Tar aging results rather than letting them go, and tar many small files into one archive to
protect the file-count quota:

```bash
tar -C /scratch3/<portfolio>/<project>/<user> -cf run_2026-03.tar member.0001 member.0002
```

---

## Hot Pools and Reported Usage

On `/scratch3-4` the first 1 GB of each file is written to a solid-state hot pool and
mirrored to spinning disk 10 to 15 minutes later. While that copy is in flight the file's
usage can appear **doubled** in quota reports.

This is expected behavior, not a quota bug and not a sign that a job is writing twice. Wait
fifteen minutes and re-check before opening a ticket.

---

## Archiving to HPSS

HPSS is the only long-term store on this system besides `/home`, and it holds a
**single copy**: there is no backup and no recovery, and `put`, `get`, and `mv`
overwrite an existing target **without warning**. Archive only what costs more
to regenerate than to store — HSMS is explicitly not an infinite resource and
quotas are being enabled.

Compute nodes cannot reach HPSS. Only the `service` partition's front ends hold
the external connection, so run transfers interactively there or in a batch job
on `service`. Load the client with `module load hpss`; it is not loaded by
default.

### hsi takes the local path first

`hsi` `put` and `get` do **not** use FTP argument order. The local pathname
comes first and a colon separates it from the HPSS pathname:

```bash
# Single file up:  LOCAL : HPSS
hsi "put /scratch3/<portfolio>/<project>/<user>/result.nc : /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"

# Retrieve into the current directory: HPSS path alone
hsi "get /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"

# Retrieve and rename:  LOCAL : HPSS
hsi "get /scratch3/<portfolio>/<project>/<user>/result.nc : /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"

hsi "get -p /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"   # keep the original mtime
```

Quote the whole command string, and use the same local-first, colon-separated
order inside a here-document. RDHPCS also mentions `hsi cput` for uploading a
directory tree, but does not publish its syntax — use `htar`, or `tar` plus
`hsi put`, which are documented.

### Size limits

| Situation | What happens |
|---|---|
| GB range | Preferred size |
| 1 TB or more | Poor performance or failure — split the file |
| **Over 3 TB** | **The store attempt fails** |
| Many MB-or-smaller files | Bundle with `htar`, or `tar` and `hsi put` the single tarball |

`htar` adds its own ceilings: member file **68 GB**, directory path **154
characters**, filename **99 characters**.

```bash
htar -P -cvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar ./results/  # -P makes the remote dir
htar -tvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar                 # list
htar -xvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar                 # extract all
htar -xvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar file1 file2     # extract named members
htar -Xvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar                 # rebuild a lost .idx
```

Creating an archive also writes a `.idx`; without it, listing and selective
extraction need a rebuild.

### Retention and expiry

Files live under a retention family — `1year` through `5year` or `permanent` —
and each family is a separate file family, so `hsi mv` works only within one
retention directory. Crossing retention pools requires `cp` and then deleting
the original. Every file gets an expiration date from its create time plus the
pool, and expired files are deleted: notification is posted on or before the
first day of the month after expiry, deletion on the first day of the second
month. It is your responsibility to check.

```bash
hsi "expls -A -R /<PORTFOLIO>/<project>/1year/<User.Id>"   # expiration dates
hsi "expfind -d 30 /<PORTFOLIO>/<project>/1year/<User.Id>" # expiring within 30 days
hsi "expfind -e 2026-03-31"                                # expired on or before a date
hsi "ls -N <path>"                                         # full details with HPSS paths
hsi "ls -V <file>"                                         # tape volumes holding the file
```

The list of files scheduled for deletion is world-readable inside HPSS at
`/Expired_Data_Lists/expired.YYYY-MM.txt` and is searchable by username.

### Getting access

HPSS access is **not** granted by being on a Hera compute project. You must
already be a current RDHPCS or WCOSS user, and then email
`rdhpcs.hpss.help@noaa.gov` with subject
`USERNAME requests access to HPSS - PORTFOLIO/PROJECT`. If you are already on
the compute project no PI or Project Firm Manager approval is needed (both are
notified); otherwise their approval is required. New projects and retention
pools are approved by the Portfolio Manager, and these requests are **not
supported in AIM** — use the HPSS help-ticket system.

The batch-job form of this is in [job-scripts.md](job-scripts.md#hpss-staging-job).
The fleet-wide reference, including the GFDL DMF archive, is in the `slurm`
skill's RDHPCS Archive Storage Reference.

Note that RDHPCS states the layout as `PORTFOLIO/PROJECT/RETENTION` while its
own command examples write `RETENTION/PORTFOLIO/PROJECT`. List your area with
`hsi "ls /"` before writing, and ask HPSS help for the canonical path rather
than guessing.

---

## What Goes Where

| You have | Put it in |
|----------|-----------|
| Source code, job scripts, dotfiles | `/home` |
| Model input you regenerate cheaply | `/scratch3` |
| Model output other jobs read next | `/scratch3` |
| Intermediate files under 30 days old | `stmp` |
| I/O-bound experimental work needing flash | `/scratch5` |
| Anything you cannot afford to lose | `/home` if it fits in 30 GB (it is backed up and snapshotted), or HPSS **plus** a second copy elsewhere |
| Data a collaborator needs long-term | HPSS or GFDL-DMF |

Three rules that RDHPCS states plainly:

1. **Never run a job against files in `/home`**, including through a symlink that points
   at scratch. Home I/O from compute jobs degrades the file system for everyone.
2. **Scratch is not storage.** It is not backed up, and a project that lapses can lose it.
   Move anything worth keeping to HPSS.
3. **HPSS is not a backup.** It keeps one copy and deletes it when the retention pool
   expires. `/home` is the only thing here that is actually backed up.

The published home quota figures disagree with each other: the queue-policy page claims
50 GB on every system, while the data-storage summary table gives Hera 30 GB and the
example `quota` output on that same page shows a smaller limit again. Use what `quota -Qs`
reports for your own account, and ask the Help Desk for more rather than assuming.
