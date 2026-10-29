---
name: rdhpcs-mercury
description: >-
  NOAA RDHPCS Mercury data-transfer system for moving data to and from
  collaborators. Use when planning a transfer to or from RDHPCS, deciding
  between Mercury trusted and untrusted data transfer nodes, placing files in
  /collab2/data or /collab2/data_untrusted, working out why /home is missing on
  a DTN, using Mercury CRON or HPSS access, or reaching Mercury through an
  RDHPCS bastion with a CAC/PIV or YubiKey certificate.
compatibility: Script-authoring skill; no login required. Access is through the mercury-mfa bastions with CAC/PIV or YubiKey credentials, and is available to all RDHPCS users.
metadata:
  version: "1.0"
  system: mercury
  facility: rdhpcs
  scheduler: none
  source: https://docs.rdhpcs.noaa.gov/systems/mercury_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# Mercury — NOAA RDHPCS Data Transfer

Mercury is "primarily a data transfer/collaboration system that is available to
all RDHPCS": a place where data can be securely copied to and from any location,
by any authorized user, to disseminate R&D data to NOAA's collaborators around
the globe. **No compute nodes are available on Mercury.** The system is made of
interactive login nodes (front ends), a file system, data transfer nodes, and
back-end HPSS storage.

## System Overview

| Component | What the guide documents |
|---|---|
| Front ends | **4 login nodes** (`mfe[01-04].fairmont.rdhpcs.noaa.gov`) |
| Hardware | dual-socket AMD EPYC Genoa 9654, 2.40 GHz, 96 cores |
| Trusted DTNs | available from trusted (pre-approved) NOAA and non-NOAA sites |
| UDTNs | available from **anywhere on the internet** |
| Back end | HPSS archive storage |

Access is with CAC or YubiKey credentials through the MFA bastion —
`mercury-mfa.princeton.rdhpcs.noaa.gov` or
`mercury-mfa.fairmont.rdhpcs.noaa.gov`.

## First Login

The directories a transfer needs are created automatically **on your first login
to a Mercury front end**:

- `/home/First.Last` — your home directory
- `/collab2/data/First.Last` — for your trusted data
- `/collab2/data_untrusted/First.Last` — for your untrusted data

Log in at least once before any sharing or untrusted transfer, otherwise the
account directories the transfer tools expect do not exist yet.

## Where Files Must Go

Choosing the path is the whole job on Mercury; pick it by **who is on the other
end**:

| Path | Front ends | Trusted DTNs | UDTNs | Quota | Purge |
|---|---|---|---|---|---|
| `/home/First.Last` | yes | **no** | no | 10 GB | not purged, backed up daily |
| `/collab2/data/First.Last` | yes | yes | yes | 60 TB | unaccessed 60 days |
| `/collab2/data_untrusted/First.Last` | yes | no | yes, as `/collab2/$USER` | 20 TB | unaccessed 14 days |

Two rules that break transfers when ignored:

1. **The `/home` tree is not accessible from the DTNs at all.** Stage into
   `/collab2` before transferring.
2. On a UDTN the untrusted tree is **renamed**: `/collab2/data_untrusted/$USER`
   appears there as `/collab2/$USER`. The UDTN view is temporary space with its
   own 5-day access-time purge, so move data into project space and clean up
   promptly — RDHPCS removes data and revokes access when that is not done.

`/collab2` is a **Lustre** scratch filesystem: it should be considered scratch,
is meant for transient data only, and is **not backed up**. "Accessed" means the
last time a file was opened for reading or writing, so a dataset you only write
once will age out. RDHPCS warns that if the filesystem nears total capacity the
purge policy may tighten (30 or 15 days), so manage the data actively.

## Transferring Data

RDHPCS encourages **Globus Connect Service** over other methods whenever
possible. It is available on Mercury through two collections:
`noaardhpcs#mercury` (trusted endpoints) and `noaardhpcs#mercury_untrusted`
(anywhere). Globus CLI is on Mercury:

```bash
module load globus-cli
```

For a laptop or workstation, Globus Connect Personal treats it as a Globus
Untrusted Endpoint; transfers suspend and resume automatically as the machine
sleeps, wakes, or reboots.

The nodes are `dtn-mercury.fairmont.rdhpcs.noaa.gov` (trusted) and
`udtn-mercury.fairmont.rdhpcs.noaa.gov` (untrusted). Trusted DTNs are reachable
by default only from some hosts inside `noaa.gov` and from pre-approved sites,
and they support ssh-based methods — `scp`, `sftp`, and `rsync` — authenticated
with your NOAA name and password plus YubiKey multi-factor authentication. A peer
that is not already reachable needs a **firewall modification request** naming the
DTN hostnames and IPs, filed with the help desk. UDTNs are open from anywhere,
including personal machines, but **unattended transfers are allowed only on the
trusted DTNs**. File space on a UDTN is deliberately limited: move data into
project space and clean up temporary files promptly.

**Tar many small files into one archive.** Transfer performance tracks the cost
of opening each file rather than the bytes moved, so a few large files beat many
small ones; RDHPCS gives the same advice for HPSS, where the alternative to `tar`
is `htar`.

## CRON, HPSS, and Software

- **CRON services are available on Mercury** for scheduled work, such as recurring
  transfers.
- **HPSS is accessible** from Mercury; see the NESCC HPSS documentation for the
  archive commands.
- Mercury carries only a **minimal software stack** for compiling and running
  programs, because it exists for data movement. Open a help ticket if you need
  something specific there.

## Common Gotchas

- Trying to run a compute job — there are no compute nodes.
- Assuming `/home` is visible on a DTN; it is not.
- Putting data for an untrusted peer in `/collab2/data`, or trusted-only data in
  `/collab2/data_untrusted` where anyone on the internet can reach it.
- Expecting `/collab2/data_untrusted` to keep its name on a UDTN — it shows up as
  `/collab2/$USER`.
- Treating `/collab2` as archive: it is unbacked-up scratch with access-time
  purges (60 days for `data`, 14 days for `data_untrusted`).
- Transferring huge file counts one by one instead of tarring.
- Expecting a full software stack, compilers, or analysis tools on a transfer node.

## Additional Resources

- Mercury user guide: <https://docs.rdhpcs.noaa.gov/systems/mercury_user_guide.html>
- Connecting and bastions: <https://docs.rdhpcs.noaa.gov/connecting.html>
- Transferring data: <https://docs.rdhpcs.noaa.gov/data/transfers.html>
- Scheduler patterns on the compute systems: see the `slurm` skill.
