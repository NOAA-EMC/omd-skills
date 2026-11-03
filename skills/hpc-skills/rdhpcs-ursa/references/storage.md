# Ursa Storage Reference

Ursa's file systems are the same NESCC systems Hera uses: Lustre on `/scratch3-4`, the
all-flash VAST file system on `/scratch5`, and HPSS for archive. Over 100 PB total, above
1000 GB/s aggregate, shared with Hera.

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
| Scratch | `/scratch3`, `/scratch4` | project-based (Lustre) | **No** | No (except `stmp`) | Routine job input and output |
| Scratch temp | `/scratch[3,4]/.../stmp` | project-based | **No** | Weekly, Monday, >30 days | Short-lived intermediates |
| VAST scratch | `/scratch5` | project quota for `rstprod` and `public` only | **No** | No | All-flash work for those two projects |
| VAST purged | `/scratch5/purged/First.Last` | 250 TB pool | **No** | Files not accessed in 90 days | Every other project's `/scratch5` access |
| Archive | NESCC-HPSS | portfolio-managed | **No — single copy** | Yes, on retention expiry | Long-term retention |

RDHPCS states plainly that the HPFS scratch file systems are **not** backed up.

---

## Checking Quota and Recovering Files

```bash
# Home usage against the quota
quota -Qs

# Where the bytes actually are
du -sh /scratch3/<portfolio>/<project>/<user>/*
```

`saccount_params` prints projects, fairshare, partition access, and per-directory
`DiskInUse`/`Quota`/`Files`/`FileQUota`, but it is documented on **Hera and Orion only** — do
not expect it on Ursa. The Ursa guide points at its own `/scratch[3,4]` usage and quota
section instead.

Quota problems on RDHPCS are usually file *count* rather than bytes: a directory of a million
small results can exhaust an inode quota while `du` reports gigabytes. Tar small files into
one archive.

`/home` keeps per-day snapshots in a directory that does not appear in `ls`, even `ls -a`, but
which you can list directly. Scratch has **no** snapshots — a file deleted from `/scratch3`
is gone:

```bash
ls /home/$USER/.snapshot/          # entries look like 2026-03-09_0015-0600.daily
cp /home/$USER/.snapshot/<daily-snapshot-name>/important.f90 .
```

The snapshot directory is available in any subdirectory of `/home`. Hourly copies appear
alongside the daily ones as `hourly.YYYY-MM-DD-HHMM`.

---

## Purge Policy

| Location | Rule |
|----------|------|
| `stmp` on `/scratch3-4` | Purged weekly on Mondays for files older than 30 days |
| `/scratch5/purged` | Purged of all files not accessed in the past 90 days |
| `/scratch3`, `/scratch4` outside `stmp` | Not purged — but never backed up |
| Node-local temp | RDHPCS documents `$TMPDIR` only for PPAN, so use a scratch `stmp` directory for intermediates |

RDHPCS says the `/scratch5/purged` schedule may be adjusted with usage, preceded by user
notification. Find files approaching the threshold before they disappear:

```bash
find /scratch5/purged/$USER -type f -atime +75
find /scratch3/<portfolio>/<project>/<user>/stmp -type f -atime +25
```

---

## `/scratch5` and the VAST File System

`/scratch5` is VAST, an all-flash file system offered alongside the Lustre `/scratch3-4`
systems. RDHPCS is explicit that it is newer and more expensive per petabyte, and that the
performance consequences for NOAA applications are not yet characterised — which is why only
two projects, `rstprod` and `public`, hold project-based quotas on it.

Everyone else works under the purged tree:

```bash
mkdir -p /scratch5/purged/$USER/$(basename "$PWD")
```

Rules for that tree:

- Create and use a **single sub-directory** under `/scratch5/purged`, named the same as the
  `First.Last` of your NOAA email.
- Users under `/purged` share a 250 TB quota.
- Nothing there is backed up, and files not accessed for 90 days are deleted.

RDHPCS asks for feedback on your experience with it, especially performance comparisons
against Lustre for your applications, through a help ticket titled `/scratch5` performance
results. If you are evaluating the file system, that ticket is part of the work.

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
**single copy**: no backup, no recovery, and `put`, `get`, and `mv` overwrite the
target **without warning**. Archive only what costs more to regenerate than to store.

Compute nodes cannot reach HPSS. Archive work runs in a partition whose nodes hold
the external connection — on Ursa that is `u1-service`, which RDHPCS names as the
target for pushing and pulling data to and from HPSS. Load the client with
`module load hpss`; it is not loaded by default.

### hsi takes the local path first

`hsi` `put` and `get` do **not** use FTP argument order. The local pathname comes
first and a colon separates it from the HPSS pathname:

```bash
# Single file up:  LOCAL : HPSS
hsi "put /scratch3/<portfolio>/<project>/<user>/result.nc : /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"

# Retrieve into the current directory: HPSS path alone
hsi "get /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"

# Retrieve and rename:  LOCAL : HPSS
hsi "get /scratch3/<portfolio>/<project>/<user>/result.nc : /<PORTFOLIO>/<project>/1year/<User.Id>/result.nc"
```

Quote the whole command string; the same order applies inside a here-document.
RDHPCS also mentions `hsi cput` for a directory tree but does not publish its
syntax — use `htar`, or `tar` plus `hsi put`, which are documented.

### Size limits

Files in the GB range are preferred. Keep any single file at or under 1 TB —
larger risks poor performance or failure — and **anything over 3 TB fails to
store**. Bundle many MB-or-smaller files with `htar`, or `tar` them and `hsi put`
the single tarball. `htar` limits: member file **68 GB**, directory path **154
characters**, filename **99 characters**.

```bash
htar -P -cvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar ./results/  # -P makes the remote dir
htar -tvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar                 # list
htar -xvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar file1 file2     # extract named members
htar -Xvf /<PORTFOLIO>/<project>/1year/<User.Id>/results.tar                 # rebuild a lost .idx
```

Creating an archive writes a `.idx` alongside it; without that index, listing and
selective extraction require a rebuild.

### Retention and expiry

Files sit under a retention family (`1year`–`5year` or `permanent`), each a
separate file family, so `hsi mv` works only within one retention directory —
crossing pools requires `cp` plus deleting the original. Every file gets an
expiration date from its create time plus the pool, and expired files are deleted:
notification on or before the first day of the month after expiry, deletion on the
first day of the second month. Checking that list is your responsibility.

```bash
hsi "expls -A -R /<PORTFOLIO>/<project>/1year/<User.Id>"   # expiration dates
hsi "expfind -d 30 /<PORTFOLIO>/<project>/1year/<User.Id>" # expiring within 30 days
hsi "ls -N <path>"    # full details including HPSS paths;  hsi "ls -V <file>" for tape volumes
```

The expired-file list is world-readable inside HPSS at
`/Expired_Data_Lists/expired.YYYY-MM.txt` and is searchable by username.

### Getting access

HPSS access does **not** follow from being on a Ursa compute project. You must be a
current RDHPCS or WCOSS user and email `rdhpcs.hpss.help@noaa.gov` with subject
`USERNAME requests access to HPSS - PORTFOLIO/PROJECT`. Already being on the
compute project means no PI or Project Firm Manager approval is needed (both are
notified); otherwise their approval is required. Projects and retention pools are
approved by the Portfolio Manager, and requests are **not supported in AIM** — they
go through the HPSS help-ticket system.

The batch-job form is in [job-scripts.md](job-scripts.md#u1-service-serial-job).
The fleet-wide reference, including the GFDL DMF archive, is in the `slurm` skill's
RDHPCS Archive Storage Reference.

RDHPCS states the layout as `PORTFOLIO/PROJECT/RETENTION` while its own examples
write `RETENTION/PORTFOLIO/PROJECT`. List your area with `hsi "ls /"` before
writing, and ask HPSS help for the canonical path rather than guessing.

---

## What Goes Where

| You have | Put it in |
|----------|-----------|
| Source code, job scripts, dotfiles | `/home` |
| Model input you regenerate cheaply | `/scratch3` or `/scratch4` |
| Model output other jobs read next | `/scratch3` or `/scratch4` |
| Intermediate files under 30 days old | `stmp` |
| I/O-bound work that needs flash, or an evaluation of VAST | `/scratch5/purged/$USER` |
| Anything you cannot afford to lose | `/home` if it fits in 30 GB (it is backed up and snapshotted), or HPSS **plus** a second copy elsewhere |
| Data a collaborator needs long-term | HPSS or GFDL-DMF |

Three rules that RDHPCS states plainly:

1. **Never run a job against files in `/home`**, including through a symlink that points at
   scratch. Home I/O from compute jobs degrades the file system for everyone.
2. **Scratch is not storage.** It is not backed up, and a project that lapses can lose it.
   Move anything worth keeping to HPSS.
3. **HPSS is not a backup.** It keeps one copy and deletes it when the retention pool
   expires. `/home` is the only thing here that is actually backed up.

The published home quota figures disagree with each other: the queue-policy page claims
50 GB on every system, while the data-storage summary table gives Ursa 30 GB and the example
`quota` output on that same page shows a smaller limit again. Use what `quota -Qs` reports for
your own account, and ask the Help Desk for more rather than assuming.
