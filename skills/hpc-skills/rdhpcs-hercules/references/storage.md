# Hercules Storage Reference

Hercules storage is administered by MSU-HPC, and its layout differs from the
NOAA-operated RDHPCS systems: a 10 GB home quota, no documented `quota -Qs`, no
documented `htar`/`hsi` examples, and a separate home filesystem shared-disk with
Orion.

---

## Filesystem Overview

| Filesystem | Path | Capacity | Quota | Backup | Notes |
|-----------|------|----------|-------|--------|-------|
| Home (NFS) | `/home/<userid>` | — | 10 GB per user | Nightly | Hercules has **its own** HFS; configs and dotfiles only |
| `work` (Lustre) | `/work/noaa/<project>` | 9 PB usable, shared with Orion | project-based, **shared with Orion** | **No** | DDN Lustre SFA18k |
| `work2` (Lustre) | `/work2/noaa/<project>` | 18 PB usable, shared with Orion | project-based, **shared with Orion** | **No** | DDN Lustre SFA18k with an SSD "Hot Pool" |
| Applications | `/apps/` | — | — | — | Read-only software tree; structure differs sharply from Orion |
| Contrib | `/apps/contrib/<package>` | — | request-based | — | Hercules has **its own** `/apps/contrib`; user-maintained software |

`/work` and `/work2` are mounted on both Orion and Hercules over a shared InfiniBand
interconnect, but they are **scratch**: MSU states the HFS is "the ONLY file system
which is backed up."

---

## Shared Disk, Separate Compute

This is the part people get wrong. MSU's own framing is that you should treat the two
systems as standalone HPC machines, with these storage exceptions:

- **Disk allocation is shared.** A project's `/work` and `/work2` quota is one pool
  consumed by both systems. Filling up on Orion blocks writes on Hercules.
- **The directory path is identical.** "Users can follow the exact same directory
  path on each system to access their data" — `/work/noaa/<project>/<user>` is the
  same tree seen from either side.
- **FairShare and core-hour usage are separate.** Consumption on Hercules does not
  draw down Orion's allocation, and reporting is per system.
- **Home is not shared.** Hercules has its own HFS, so dotfiles, scripts, and keys
  you set up on Orion must be set up again on Hercules.
- **`/apps/contrib` is not shared.** A contrib package built for Orion is not
  automatically present on Hercules.

---

## Which Lustre Filesystem to Use

Every NOAA project received an allocation on both. MSU's advice is empirical:
`/work2` has more than twice the capacity of `/work` and its SSD tier can improve
small-file performance and random I/O, so **try both and keep whichever measures
better for your workload**. Do not assume `work2` is automatically faster.

---

## Checking Quota and Usage

`saccount_params` is the documented tool (load the NOAA tooling first). It prints
your home quota in MB, then one block per project with FairShare, core hours used
over 30 days, the 30-day allocation, the project directory, and disk and file usage:

```bash
module load contrib noaatools
saccount_params
```

Example shape of the home line from MSU's guide:

```
Home Quota (/home/<userid>)   Used: 1035 MB   Quota: 8192 MB   Grace: 10240
```

Note the quota is reported in **MB** (8192 MB = 10 GB), while the project lines
report GB. A windfall-only project shows an allocation of 1 and lists only
`windfall` under Available QOSes.

Other documented reports:

```bash
shpcrpt -c hercules -s        # core-hour usage on Hercules; all projects you can see
shpcrpt -c hercules -p <project>
reportFSUsage                 # Lustre quota and usage report
du -sh $HOME                  # home usage against the 10 GB quota
```

`reportFSUsage` prints a "LUSTRE QUOTA AND USAGE REPORT" with columns
`Directory/Group`, `Usage (GB)`, `Quota (GB)`, `Limit (GB)`, `Files`, and
`Percentage`, and marks an over-quota project with `**`.

Use `-c hercules` for Hercules usage. Since disk is shared but compute is not, read
`reportFSUsage` for the combined picture and `shpcrpt -c hercules` for the
per-system compute picture.

The `quota -Qs` command RDHPCS documents for Gaea, Ursa, Hera, and Mercury is **not**
documented for Hercules, and RDHPCS publishes no `lfs quota` guidance for the MSU
systems either. There is no `account_params` alias — MSU states you must use
`saccount_params`.

---

## File Counts

The Lustre report tracks a `Files` column against a per-project file quota, so a
project can be blocked by inode pressure while still under its byte quota. The
standard remedy applies: pack many small files into a tar before writing them, and
clean up restart and checkpoint debris rather than keeping every cycle.

---

## Home Directory

- NFS, **10 GB** per user, backed up nightly — the only backed-up filesystem.
- This HFS is **Hercules-only**. Nothing in it is shared with Orion.
- The directory is **deleted when your account is deleted**, and deleted HFS data is
  not recoverable. Accounts are scheduled for deletion two weeks after an un-renewed
  expiry date, and lock after 90 days of inactivity.
- Project data on `/work` and `/work2` survives an individual user's deletion.

RDHPCS's fleet data-storage page describes an online `~/.snapshot` backup tree with
`hourly.*`, `daily.*`, and `weekly.*` snapshots. That page does not name Hercules,
and the MSU guide documents only "backed up on a nightly basis", so **do not promise
a `.snapshot` recovery path on Hercules** — ask the help system to restore from the
nightly backup.

Do not run jobs against files in `/home`, and do not point `-o`/`-e` there: it is
small, NFS, and shared.

---

## Transferring Data In and Out

| Method | Endpoint | Use |
|--------|----------|-----|
| SCP / SFTP | `hercules-dtn-1.hpc.msstate.edu` … `hercules-dtn-4`, or `hercules-dtn.hpc.msstate.edu` (DNS round-robin over `hercules-dtn-{1..4}`) | Direct copies |
| Globus | endpoint `msuhpc2-Hercules` | Large or bulk transfers, Globus File Manager app or CLI |
| Open OnDemand | Hercules web portal | Browser file management, job submit/monitor, remote desktop |

MSU recommends **Globus** for bulk movement because of limited network bandwidth.
You authenticate to the DTNs and the portal with your MSU username, password, and
Duo. Note that Globus endpoints are per system: `msuhpc2-Orion-dtn` and
`msuhpc2-Hercules` are different endpoints, even though they land in the same shared
`/work` tree.

Development nodes (`hercules-devel-1`, `hercules-devel-2`) are SSH-reachable from
inside only.

---

## `/apps` and `/apps/contrib`

`/apps/` holds the supported software tree. MSU states the `/apps` directory
structure is **significantly different** between Orion and Hercules, so no `/apps`
path you know from Orion is valid here.

`/apps/contrib/<package>` is user-maintained software that MSU creates **on request
through a help desk ticket**. The development nodes are the only gateway for writing
into `/apps/contrib/`, so a build that installs there must run on `hercules-devel-*`,
not on a login node or in a batch job. Hercules' `/apps/contrib` is its own directory
— a package maintained for Orion is not visible here.

Most open-source packages on Hercules are spack-built into
`/apps/spack/<package-hash>`, and the hash changes on every rebuild, which MSU says
"may occur often." Never hard-code a spack path into a script or a module; load a
module instead.

---

## Archiving

The `service` partition's front-end nodes hold the external connection, so MSU places
HSMS/HPSS push and pull workflows there (1 core, 24 hours). The MSU-HPC guide does
**not** publish `hsi` or `htar` command examples for Hercules, and the RDHPCS
archiving page describes NESCC's HPSS on the NOAA-operated systems. Before writing an
archive script for Hercules, confirm the approved commands and the correct
`module load` line with the help system at `rdhpcs.orion.help@noaa.gov`.

MSU's published Best Practices are worded about Orion ("Due to limited disk space on
Orion, it is highly recommended that data be moved back to the R&D HPC Niagara
system", and use Globus for the move). Because your disk allocation is shared between
the systems, that advice effectively applies to Hercules data as well: the default
long-term path is Niagara, not HPSS. Access to Niagara requires an active RDHPCS
account in addition to your MSU account.

---

## What Goes Where

| Data | Location |
|------|----------|
| Dotfiles, small configs, SSH keys | `/home/<userid>` (Hercules HFS — set up separately from Orion) |
| Source and build trees | `/work/noaa/<project>/<user>` or `/apps/contrib/<package>` |
| Model input, output, restarts | `/work/noaa/<project>/<user>` (test `work2` for small files) |
| Job stdout/stderr | `/work/noaa/<project>/<user>` — never `/home` |
| Software shared with collaborators | `/apps/contrib/<package>` (help ticket, written from `hercules-devel-*`) |
| Data no longer in active use | Niagara, via Globus |
