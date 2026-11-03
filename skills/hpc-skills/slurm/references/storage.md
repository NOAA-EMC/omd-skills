# RDHPCS Archive Storage Reference

Long-term archiving on NOAA RDHPCS: NESCC-HPSS and the GFDL DMF archive. Both
hold single copies of your data on tape, so the rules below are about not losing
files, not about convenience.

---

## Which Archive

| Archive | Reachable from | Use it for |
|---|---|---|
| NESCC-HPSS | Hera, Ursa, Mercury, Gaea DTNs, WCOSS2 | Shared RDHPCS project data, all portfolios |
| GFDL DMF | PPAN and other GFDL systems (read-only from GFDL workstations) | GFDL-model data under `/archive` |

GFDL users can write to HPSS from any RDHPCS system via the Princeton DTN or the
Princeton Globus endpoint; the reverse path (RDHPCS systems writing to DMF) is
not documented.

MSU-operated Orion and Hercules are not HPSS front ends in the RDHPCS
documentation, and their default long-term path is Niagara. Do not write HPSS
workflows for those two systems without confirmation from RDHPCS help.

---

## The Three Rules That Cause Data Loss

1. **Single copy.** Both archives state that all data is single copy and that
   deleted data cannot be recovered. There is no backup. `hsi` `mv`, `put`, and
   `get` overwrite an existing target **without warning**, so set directory
   permissions deliberately before writing. (A damaged DMF tape is the one
   exception: staff attempt manufacturer recovery, which sometimes fails.)
2. **Retention is not optional.** Files are assigned an expiration date from
   their create time plus the retention pool they were written to, and are
   deleted on expiry. Deleted-by-expiry data is gone.
3. **Archive only what is worth more than regenerating.** HSMS is explicitly
   "not an infinite resource" and quotas are being enabled. Recomputing from
   inputs is often cheaper than long-term storage.

---

## Getting HPSS Access

Being on a compute project does **not** give you HPSS access. You must already
be a current RDHPCS or WCOSS user, then request it:

- If you are already on the compute project, no PI or Project Firm Manager
  approval is needed, but both are notified. Otherwise PI/PfM approval is
  required.
- Email `rdhpcs.hpss.help@noaa.gov` with subject line
  `USERNAME requests access to HPSS - PORTFOLIO/PROJECT`.
- New projects and retention pools are approved by the Portfolio Manager.
- These requests are **not supported in AIM**; they go through the HPSS help-ticket system.

---

## Where Files Live: Portfolio, Project, Retention

HPSS data is organized by portfolio, project, and retention period. The
documented layout is `PORTFOLIO/PROJECT/RETENTION`, and HPSS looks like that:

```text
/BMC/GEFS_D/5year/<your-user-id>/
```

Note that the documentation's own command examples write paths the other way
round (`/1year/BMC/testproj/...`), because each retention period is a separate
**file family** mounted at the root. Do not guess — list your area with
`hsi "ls /"` and `hsi "ls -l <path>"` before writing, and ask help for the
canonical path for your project.

Portfolios in use include `NCEPPROD`, `NCEPDEV`, `BMC`, `HFIP`, `CPO`,
`NAGAPE`, `NOS`, and `SYSADMIN`.

Retention families are `1year`, `2year`, `3year`, `4year`, `5year`, and
`permanent`. Because each family is a separate file system:

- `hsi mv` works only **within** one retention directory.
- Moving between retention pools requires `hsi cp` and then deleting the
  original.

---

## Loading the Tools

HPSS tools are not loaded by default:

```bash
module load hpss          # Hera, Mercury, Ursa, WCOSS2
```

On Gaea the module file lives elsewhere:

```bash
module use /usw/hpss/modulefiles
module load hsi
```

`hsi` is an interactive program; the one-shot form is `hsi "command"` — note
that the whole command string must be quoted.

---

## hsi put and get: Local Path First

HPSS `get` and `put` **do not** use FTP argument order. The local pathname
comes first and is separated from the HPSS pathname by a colon:

```bash
# put: LOCAL : HPSS
hsi "put /home/user/work/run.nc : /BMC/GEFS_D/5year/user/run.nc"

# get into the current directory: HPSS path only
hsi "get /BMC/GEFS_D/5year/user/run.nc"

# get and rename: LOCAL : HPSS
hsi "get /home/user/restored/run.nc : /BMC/GEFS_D/5year/user/run.nc"

# -p preserves the original modification time
hsi "get -p /BMC/GEFS_D/5year/user/run.nc"
```

The same order applies inside a here-document:

```bash
hsi << EOF
put /home/user/work/run.nc : /BMC/GEFS_D/5year/user/run.nc
get /home/user/restored/run.nc : /BMC/GEFS_D/5year/user/run.nc
EOF
```

`hsi cput` is also mentioned for directory trees, but RDHPCS does not publish its syntax; `htar` or `tar` plus `hsi put` are documented.

---

## File Size Rules

| Situation | Guidance |
|---|---|
| GB range | Preferred size for archive files |
| Under 1 TB | Recommended ceiling for a single file |
| 1 TB or more | Risk of poor performance or failure; split it |
| **Over 3 TB** | **The store attempt will fail** |
| MB or smaller, many files | Do not archive individually — bundle with `htar`, or `tar` and `hsi put` the single tarball |

`htar` adds its own limits: a member file cannot exceed **68 GB**, a directory
path **154 characters**, or a filename **99 characters**.

```bash
htar -P -cvf /BMC/GEFS_D/5year/user/out.tar /home/user/work/out   # create (-P makes the remote dir)
htar -tvf /BMC/GEFS_D/5year/user/out.tar                          # list
htar -xvf /BMC/GEFS_D/5year/user/out.tar                          # extract everything
htar -xvf /BMC/GEFS_D/5year/user/out.tar file1 file2              # extract named members
htar -Xvf /BMC/GEFS_D/5year/user/out.tar                          # rebuild a missing .idx
```

Creating an archive also writes a `.idx` file. Keep it — without it, listing
and selective extraction require rebuilding the index.

---

## Checking What You Have and What Is Expiring

```bash
hsi "ls -N /BMC/GEFS_D/5year/user"      # full details including HPSS paths
hsi "ls -V <file>"                       # tape volumes holding the file
hsi "expls -A -R /BMC/GEFS_D/5year/user" # expiration dates: -A absolute, -R recursive
hsi "expfind -d 30"                      # expiring within 30 days
hsi "expfind -e 2026-03-31"              # expired on or before that date
hsi "expfind -b 2026-01-01 -e 2026-03-01" # window; with neither flag, all expired files
```

Notifications for expired data are posted on or before the first day of the
month after expiry, and deletion happens on the first day of the second month
after. The list of affected files is world-readable inside HPSS:

```bash
hsi "get /home/user/expired.txt : /Expired_Data_Lists/expired.2026-03.txt"
```

It is searchable by username, and it is your responsibility to check it.

---

## Batch Jobs That Touch HPSS

Compute nodes cannot reach HPSS. Run transfers on a front end interactively, or
submit to the service/transfer resources. The documented partitions are:

| System | Partition | Notes |
|---|---|---|
| Hera | `service` | 1 task, short walltime |
| Mercury | `service` | 1 task, short walltime |
| Ursa | `u1-service` | 1 task, short walltime |
| Gaea | `dtn_f5_f6` | add `--constraint=f5` or `--constraint=f6` for the node with that file system mounted |

A minimal staging job, taking the module line from the machine it runs on:

```bash
#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --time=0:30:00
#SBATCH --account=<valid project>
#SBATCH --partition=<see the table above>
#SBATCH --qos windfall
#SBATCH --job-name=hpss-stage

source $MODULESHOME/init/bash
domainname=$(perl -T -e "use Net::Domain(hostdomain)")
if [[ $domainname =~ fairmont ]]; then
    module load hpss
elif [[ $domainname =~ ncrc ]]; then
    module use /usw/hpss/modulefiles
    module load hsi
fi

cd "$SLURM_SUBMIT_DIR"

# Skip the upload if the archive index already exists
if hsi "ls -l ${hpssdir}/${tarfile}.idx" > /dev/null 2>&1; then
    echo "$tarfile already saved."
    exit 0
fi

htar -P -cvf "${hpssdir}/${tarfile}" "$dirsave" || { echo "create failed"; exit 3; }
```

On Gaea, prefer requesting a transfer QOS instead of guessing a partition:

```bash
sbatch --qos hpss  ...   # transfer to or from NESCC HPSS
sbatch --qos ppan  ...   # transfer to or from GFDL / PPAN
sbatch --qos dtn   ...   # default QOS on the Gaea DTNs
```

All three are capped at 16 hours with a usage factor of 1.00. These QOS
definitions are paused when the matching service is under maintenance, so a
stuck `hpss` or `ppan` job may be the maintenance, not your script. Inspect
them with `sacctmgr show qos format=name,priority,usagefactor,maxwall`.

---

## GFDL DMF Archive

The GFDL archive is HPE DMF-based and is reachable from PPAN and other GFDL
systems. Each user gets `/archive/$USER`, which is a symlink into one of the
per-user-file-system targets `/arch[0-9a-f]/$USER`.

| Command | What it does |
|---|---|
| `dmget <file>` | Stage an archived file back to disk (opening a file also triggers auto-recall) |
| `dmput <file>` | Write a file to the archive |
| `dmwho` | Show your queued DMF requests |
| `dmls -l` | List with offline/online state |
| `dmlocate <pattern>` | Locate files across the archive from a daily-updated database |
| `archrpt -s \| -r <group>` | Archive usage reports (administrative enforcement) |

Practical constraints:

- Copy recalled data to `/vftmp` before working on it.
- Suited to large files; avoid archiving many small files.
- There is **no set retention policy** — data stays until it is removed.
- Read and write from the analysis cluster; GFDL workstation access is
  **read-only**.
- GFDL users can write to HPSS from any RDHPCS system using the Princeton DTN
  or the Princeton Globus endpoint.
- Help: `oar.gfdl.help@noaa.gov`.

---

## Documentation Contradictions to Verify Before Relying On

The RDHPCS archive pages disagree with each other in three places. Confirm with
`rdhpcs.hpss.help@noaa.gov` rather than trusting any single page:

1. **Path order.** The stated structure is `PORTFOLIO/PROJECT/RETENTION`, while
   the examples use `RETENTION/PORTFOLIO/PROJECT`.
2. **Which systems reach HPSS.** The archive page lists WCOSS2, Ursa, Hera,
   Mercury, and Gaea; the getting-started page omits Mercury.
3. **Home filesystem backup.** The storage page says `/home` is backed up
   nightly; the policies page says it is "backed up regularly" and points at
   snapshots instead.
