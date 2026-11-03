---
name: rdhpcs-cloud
description: >-
  NOAA RDHPCS Cloud computing on the Parallel Works platform, plus Parallel
  Works access to on-prem RDHPCS systems. Use when creating a custom HPC
  cluster on demand through the NOAA RDHPCS Portal, running Jupyter or VS Code
  on a Slurm compute node in a cloud cluster, choosing Lustre, bucket or blob,
  or contrib NFS storage, fixing the $HOME/pw quota warning that Parallel Works
  triggers on an on-prem system, estimating cost with the PW cost calculator or
  real-time dashboard, watching the project allocation freeze thresholds, or
  moving cloud data with Globus and its egress charges.
compatibility: Script-authoring skill; no login required. Using the cloud needs a NOAA account, a project allocated to a cloud resource, and sign-in through the NOAA RDHPCS Portal with CAC or YubiKey.
metadata:
  version: "1.0"
  system: cloud
  facility: rdhpcs
  scheduler: slurm
  source: https://docs.rdhpcs.noaa.gov/systems/cloud_user_guide.html
  as_of: "2026-10-28"
allowed-tools: Read Write Grep Glob
---

# RDHPCS Cloud

"The RDHPCS Cloud Platform allows NOAA users to create a custom HPC cluster on
an as-needed basis." Cloud computing is managed by the **Parallel Works**
platform across **Amazon Web Services, Google Cloud Platform, and Microsoft
Azure**, reached through the NOAA RDHPCS Portal, which is customized for NOAA.
The same platform **can also manage on-premise resources, with identical
operation**, so a Parallel Works session may be driving a cloud cluster or an
on-prem RDHPCS system.

## Two Ways to Use It

| Mode | What it is | Who governs the work |
|---|---|---|
| Cloud cluster | You configure and start a cluster; Slurm runs inside it | Your project's allocation and the cluster's partitions |
| On-prem access | Parallel Works authenticates to an on-prem HPC system | That system's own rules still apply |

Sign-in: log into the Parallel Works NOAA Portal, click **Continue with NOAA
SSO** using your NOAA username, authenticate with **CAC or YubiKey**, then use
the **Compute** tab. On that tab the power button starts and stops clusters, the
node-status indicator shows resources in use, the status indicator shows
Active/Stopped, the gear opens the cluster configuration, and the **"i" button
shows the login-node IP address** to use when logging into the master node.

Cloud projects start with `ca-` (AWS), `cg-` (GCP), or `cz-` (Azure), and you
must be on a project allocated to a cloud resource to use one. Parallel Works
access to on-prem systems is permitted only from a published list of countries.
Requests for a project or an allocation go through AIM, the RDHPCS Allocation
Committee form, and a cloud help-desk ticket.

## Interactive Work

Run Jupyter and VS Code on a **compute node**, not the head node:

- **Jupyter** — the Jupyter workflow is in the ACTIVATE Marketplace and runs on a
  Slurm compute node. Set *Directory To Start Jupyter Lab GUI* to your session's
  default path, and make sure a partition provides the instance type you need —
  GPU work requires configuring a partition with a GPU instance type, since the
  marketplace default ships only `compute` and `batch`.
- **VS Code** — either a VS Code **session** with *Compute Target → Request new
  worker* (which provisions a new node), or the VS Code **workflow** with the
  *Schedule Job* toggle set to **Yes** plus the Slurm submission information.
- **From the head node** — you can `ssh` to a compute node by hostname without a
  job on it, provided the node is powered on. Check first:

  ```bash
  sinfo
  squeue
  ssh compute-dy-c5n18xlarge-1
  ```

  Most configurations suspend idle compute nodes, so `idle~` means asleep.

## Storage

Three storage types are available on a cluster:

| Type | What it is | Cost notes |
|---|---|---|
| Lustre | parallel filesystem, ephemeral or persistent; attach and mount from the Storage tab | accessible **only from an active cluster**; "expensive"; resize in 2.8 TB chunk multiples |
| Bucket / blob | object containers — S3 bucket (AWS), bucket (GCP), Blob (Azure, which acts as bucket *and* NFS) | AWS/GCP projects may create and mount many buckets; the project default bucket is reachable from the public domain using keys |
| contrib | project software library and team collaboration, like on-prem contrib; built on native NFS (EFS, Azure Files, GCP) | AWS **0.30 USD per GB per month on usage**; Azure on usage; **GCP on allocated volume — default 2.5 TiB is about 768 USD per month** |
| `/home` on the head node | personal workspace; Parallel Works also writes its `$HOME/pw` copy area here | RDHPCS publishes no cloud home quota figure, so do not assume one |

Because GCP and Azure price contrib on *provisioned* capacity, an unused default
contrib volume still bills. Older projects can have it removed by emailing the
cloud help desk with the subject **Remove Contrib Volume**.

For transfers, RDHPCS recommends **Globus** wherever applicable: it is secure and
auditable, and a Globus Connect Personal endpoint on a cluster handles larger
files. Note that **all egress charges from a cloud Globus transfer are applied to
the project — including data stored in a public, free-to-access repository such
as the NOAA Open Data Dissemination (NODD) program**. Parallel Works bucket
credentials reset after **12 hours** for security; the PW token service issues a
token valid up to 24 hours for provider or PW CLI use.

## Quota Warnings from Parallel Works

The quota failure people hit runs opposite to what they expect: **Parallel Works
copies programs and data files into `$HOME/pw` on the system it is driving**, so a
workflow on an on-prem system can exceed that system's home quota. The guide's own
example is running the VS Code workflow **on Hera**, where `$HOME` is small. Move
the directory to project space and symlink it back:

```bash
# if $HOME/pw already exists on the system reporting the quota error
mv $HOME/pw /a/directory/in/your/project/space/pw
ln -s /a/directory/in/your/project/space/pw $HOME/pw

# if it does not exist yet, create it in project space first
mkdir -p /a/directory/in/your/project/space/pw
ln -s /a/directory/in/your/project/space/pw $HOME/pw
```

## Cost and Allocation Governance

Estimate before running. The **Cost Calculator** (Resources tab → double-click
the resource definition → Definition tab) shows a dynamic hourly estimate once
you set the compute and Lustre sizes: multiply by run time for one experiment
(10 USD/hour × 2 hours = 20 USD), then by the number of runs for a project
allocation (100 runs × 20 USD = 2,000 USD). The **Cost dashboard** gives
near-real-time session costs — set Time Filter to **RT**, keep User Filter on
your name, and expect a refresh every 5 minutes. For core-hours, remember that
**in GCP two vCPUs make
one physical core** (`a2-highgpu-1` = 12 vCPUs = 6 cores), so 1 node × 4 hours ×
6 cores = 24 core hours. Runtime is not the whole bill: contrib filesystem,
object storage for backups, and egress all cost money.

Project allocation actions escalate automatically:

| Usage | What happens |
|---|---|
| 85% | email to PI, tech lead, and admin; clusters and jobs continue; warning on the dashboard |
| 90% | no new cluster and no new jobs; running clusters continue; you must move data out of contrib and object storage; "Freeze" on the dashboard |
| 95% | all compute resources terminated and removed; bucket and `/contrib` data remain, only object storage is directly available; project disabled |
| 99.5% | resources manually removed; COR/ACORS, PI, tech lead, accounting lead notified |

Reporting: the PW cost dashboard, a **daily NOAA Cloud Usage Report** to project
PIs and tech leads, and a **monthly** report covering all cloud projects for
portfolio managers and PIs. Best practices to avoid surprises: enable **runtime
alerts**, set a **session cost limit**, watch the Monitor → Instances panel, use
the Cost dashboard to spot anomalies, and when stopping a cluster choose
**Destroy** unless you must preserve boot-disk changes — **Hibernation** keeps
custom software but keeps charging for the boot disk.

## Job Scripts

Slurm inside a cloud cluster uses the same directives as the on-prem systems, but
the node shape is whatever the cluster's partitions provide — instance types such
as `c5n.18xlarge` with a `max_node_num` bound and dynamic node names like
`compute-dy-c5n18xlarge-[2-5]`. Worker nodes are provisioned on demand when a job
reaches the queue. Read the live shape instead of reusing an on-prem number:

```bash
sinfo -N -l
scontrol show node | head -20
```

## Common Gotchas

- Assuming a Parallel Works session is its own scheduler when the on-prem system
  it drives still governs the work.
- Running Jupyter or VS Code on the head node instead of requesting a worker or
  compute node.
- Letting `$HOME/pw` fill an on-prem home quota — symlink it to project space.
- Treating Lustre as durable archive: it is only accessible from an active
  cluster, and it is expensive.
- Leaving a GCP default contrib volume attached and paying for allocated
  capacity you are not using.
- Expecting Parallel Works bucket keys to stay valid (12-hour reset).
- Ignoring egress charges when using a Globus endpoint out of the cloud, even for
  NODD data.
- Crossing 90% of the project allocation and losing the ability to start
  anything.
- Choosing **Hibernation** out of habit and continuing to pay for the boot disk.

## Additional Resources

- RDHPCS Cloud guide: <https://docs.rdhpcs.noaa.gov/systems/cloud_user_guide.html>
- Parallel Works user guide: <https://parallelworks.com/docs>
- Cloud help desk: `rdhpcs.cloud.help@noaa.gov`
- On-prem scheduler patterns: see the `slurm` skill.
