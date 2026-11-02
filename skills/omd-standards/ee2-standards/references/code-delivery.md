# Code Delivery and Vertical Structure

> **[WCOSS]** The branch and tag naming (`release/vX.Y`, `bugfix/…`, `hotfix/…`,
> `vX.Y-rc<#>`), the Lmod modulefiles, and the sorc/exec/parm/fix/ush/jobs vertical
> structure are the NCO delivery contract reviewed at hand-off.

## Code Delivery and Vertical Structure

### A. Code Delivery

Delivered code must:

* contain any production bug fixes implemented since the last code delivery.
* only contain changes that were defined at project kickoff, and are needed for the production environment.

All new packages will be delivered via git-based services (e.g. GitHub, GitLab).

Production code delivered via git (and hosted on GitHub) will be held to the following requirements on naming conventions and procurement:

Code must exist on a distinct branch for delivery.

* Branch names for upgrades (versions `vX.Y`) will use one of the following naming conventions:

  * For code that is intended for review by the NCO SPA team, use `release/vX.Y`.
  * For repositories that support more than one model, use `release/<model>.vX.Y`.

* Branch names for bugfixes, hotfixes, and routine maintenance (versions `vX.Y.Z`)  will use one of the following naming conventions:

  * For maintenance patches and non-critical bugs, use `bugfix/<short_description>`
  * For critical production bugs, use `hotfix/<short_description>`

When NCO and a development team agree that they are ready to implement changes on a `bugfix/` or `hotfix/` branch, both teams will make a joint decision about the specific version number that will be used for implementation. A tag must be created to reflect the chosen version number.

* Release tags will follow these naming conventions:

  * For code that is intended for review by the NCO SPA team, use `vX.Y-rc<#>` to indicate release candidates on `release/` branches.

    * Begin release candidate numbering at 0 and increment for each change set that NCO places into parallel or evaluation.
    * Release candidate tags should exist only on `release/` branches.

  * For code that is intended for production implementation, use `vX.Y.Z`.

NCO SPA team members must be able to procure code deliveres with the following git commands.

For code that is intended for review by the NCO SPA team:

```bash

$ git clone git@github.com:<organization>/<repo_name>.git <model_name>.<branch_name>
$ cd <model_name>.<branch_name>
$ git checkout <branch_name>
```
For code that is approved for a production implementation:

```bash

$ git clone -b <model_name>.vX.Y.Z git@github.com:<organization>/<repo_name>.git <model_name>.vX.Y.Z
$ cd <model_name>.vX.Y.Z
$ git switch -c <model_name>.vX.Y.Z
```
### B. Source Code Compilation (C or Fortran)

The directory structure, compilation scripts, makefiles, and documentation for building must be understandable to someone unfamiliar with the specifics of your model.
Do not deliver pre-built executables or libraries to IDSB. It is the SPA's responsibility to build all code before it is run in production.

* If more than one executable is to be built, divide the source files into sub-directories according to the executable they produce.
* The only exception is if multiple executables share a large portion of their code base in which case sub-directory sharing is allowed.
* The name of each source directory must be the name of the executable it produces plus the appropriate extension (.cd or .fd for C or Fortran code, respectively).
* If multiple executables are produced then their names must resemble the base source directory name.
* All source code must be delivered with a build script, and optionally a module file, used to set up the build environment.
* It must define the compiler and its version (by loading the appropriate versioned compiler), specific library versions, and all other external files used to compile the application.
* An example modulefile can be found in Example 12 of Appendix A: Workflow Examples. Creating symbolic links to external resources (e.g. to absolute paths) is not allowed.
* The modulefile or script *must not* reference unused software.
* WCOSS uses the Lmod environmental module system, therefore all module files must be in Lmod/Lua format
* Each source code directory must have a makefile that does everything needed to build the executable.
    For example, `global_fcst.fd` would contain Fortran code and a makefile to produce the `global_fcst` executable.
* The basic '`make`' command must not move the compiled binary; however, '`make install`' may do so.
* The makefile *must not* include references to unused libraries. Example 13 of Appendix A: Workflow Examples contains an example.
* See Environment Equivalence (EE) standards for more details about builds
* The resulting executable(s) must continue to work if the original build path is removed or renamed (eg, when moving the package from ops/para to ops/prod).
* There are four critical targets that must be defined in every makefile. They are `all`, `debug`, `install`, and `clean`.
* Additionally, a `test` target is required to run unit tests for libraries and utility programs.
* Example 13 of Appendix A: Workflow Examples contains an example of each.
* The `debug` target must minimally contain the `check all` and `ftrapuv` flags in fortran or their equivalent in other accepted languages
* Use a readme file in the source directory to explain the build process, particularly if it requires any interaction or if it is non-standard in any way;
    for example, in situations where a makefile produces more than one executable.
* Clear, concise instructions (see Example 10 in Appendix A: Workflow Examples) will reduce confusion and errors if it becomes necessary to rebuild the executable quickly.

### C. Directory Structures

All components of an application to be implemented into the production environment are required to be in vertical structure, where, with the exception of system or standard production libraries and input data, all of the files required to completely build and run the jobs are contained in an application-specific package.
The package must contain all `J-jobs` and `ex-scripts` specific to the model and must be named with the following format: `model.vX.Y.Z` (e.g. `gfs.v12.0.1`).
Files must be organized into sub-directories according to their type (see Table 3).
If there exists code, scripts or other files shared between multiple models then they must reside in a separate shared package (e.g. `model_shared.v5.0.0`).
Shared packages must not contain `J-jobs` or a jobs sub-directory. Shared packages must be backward compatible.

**Table 3: Package Sub-directories**

| Subdirectory | Description |
| --- | --- |
| `doc` | release notes or other documentation |
| `jobs` | J-jobs |
| `scripts` | ex-scripts |
| `ush` | utility scripts (ush-scripts) |
| `sorc` | source code that can be compiled |
| `exec` | binary executables |
| `parm` | parameter files |
| `parm/wmo` | Specific subdirectory under ./parm for WMO GRIB headers |
| `fix` | fixed fields, tables or other static input data |
| `lib` | model-specific libraries |
| `ecf` | ecFlow scripts and definition files |
| `gempak` | all gempak-related files |
| `versions` | contains run.ver and build.ver, which are files that get automatically sourced in order to track package versions at run time and compile time, respectively (e.g., "export bufr_ver=11.4.0; export gempak_ver=7.3.3"; export lmp_ver=v2.4.0. The "v" is excluded for module versions). |
| `modulefiles/` | model module files |
Table 4 lists the primary data and application directories used within the WCOSS NCO production environment.
These directories can be located using the variables defined in the `prod_envir` module (see Example 7 in Appendix A: Workflow Examples).

**Table 4: WCOSS directory structure**

| Directory | Description |
| --- | --- |
| `prod` | applications/packages in the production suite |
| `test` | applications/packages in the test suite (unscheduled) |
| `para` | applications/packages in the parallel suite (scheduled) |
| `${envir}/com` | data and application output, including outgoing products |
| `${envir}/dcom` | incoming data (retrieved from outside WCOSS) |
| `${envir}/brs` | backup of production packages |
| `${envir}/tmp` | temporary working directories for running jobs |
Data from external sources is stored in `dcom` and model output is stored in `com`.
The output folder of the com directory contains PBS Pro job stdout and stderr.
World Meteorological Organization (WMO) headed output products are placed in a model's com structure under a `wmo` subdirectory.
Model output products in GEMPAK format (grids, model vertical profiles) are placed in the model's com structure under a `gempak` subdirectory.
Table 5 (below), Table 7, Table 8, and Table 9 (in Appendix B: Variables and Directory Structure Tables) show the structures of com, and dcom directories, respectively.

> **Upstream note:** the source prose ("Table 5 (below), Table 7, Table 8, and Table 9…")
> references a **Table 7** that the upstream document never defines. Tables 1–6, 8, and 9 are
> present; Table 7 is a gap in the source, preserved here rather than reconstructed.

**Table 5: Structure of COM directories**

| `/lfs/h1/ops/` subdirectory | Description |
| --- | --- |
| `prod/com/NET/$ver/RUN.YYYYMMDD` | production model output for a day |
| `test/com/NET/$ver/RUN.YYYYMMDD` | test model output for a day |
| `para/com/NET/$ver/RUN.YYYYMMDD` | parallel model output for a day |
| `prod/com/output/YYYYMMDD` | production job stdout/stderr for a day |
| `test/com/output/YYYYMMDD` | test job stdout/stderr for a day |
| `para/com/output/YYYYMMDD` | parallel job stdout/stderr for a day |
| `prod/com/output/transfer/YYYYMMDD` | transfer job stdout/stderr for a day |
| `prod/com/output/logs` | log files |
### D. NCO Labeled Issues and Bugzilla Bugs
Before handing off code to NCO, all pre-existing NCO labeled issues and/or Bugzilla Bugs (hereafter simply "Bugzillas") must be addressed.

The SPA will then verify the fix during testing and close the issue/Bugzilla following implementation.

If an NCO labeled issue or Bugzilla cannot be resolved, justification must be added in a comment on the issue/Bugzilla and approval received from the SPA Team Lead.

#### i. Issue Tracking on Remote Hosting Services

| NCO Issue Label | Description |
| --- | --- |
| NCO Type: Bug | A bug that was identified in production code or during NCO review |
| NCO Type: Standards | An item in the standards document needs to be addressed |
| NCO Type: Enhancement | A suggested improvement from NCO |
| NCO Status: Open | An NCO issue that has yet to be worked on by the development team |
| NCO Status: In Progress | An NCO issue that is actively being worked on |
| NCO Status: Review Required | An NCO issue that has been addressed, but requires review from NCO SPA team member |
Please mark all items that have been resolved with "NCO Status: Review Required" and explain the resolution, including a link to a pull request which addresses the issue.

#### ii. Bugzillas

NCO will be transitioning from Bugzilla to issue tracking on remote hosting services (e.g., GitHub).

Please continue to mark all Bugzillas that have been resolved as such and explain the resolution, including relevant files modified to address the Bugzilla.

## Review checklist

- **[WCOSS]** Releases use `release/vX.Y`; bug fixes use `bugfix/<short_description>`;
  emergency fixes use `hotfix/<short_description>`; production tags use `vX.Y.Z` and
  release-candidate tags use `vX.Y-rc<#>`, with release-candidate numbering starting at 0.
- **[WCOSS]** Every delivery ships a build script and, optionally, a modulefile that pin the
  compiler and library versions; the modulefile and makefile must not reference unused
  software or libraries.
- **[WCOSS]** All modulefiles are Lmod/Lua format, and a modulefile must not create symbolic
  links to external resources (e.g. to absolute paths).
- **[WCOSS]** The package follows the vertical structure (sorc/exec/parm/fix/ush/jobs per
  Table 3), and no pre-built executables or libraries are delivered to IDSB — the SPA builds
  all code before production.
