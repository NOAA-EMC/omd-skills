# Standards

## Standards

### A. General Application Standards

Diagnosing failures quickly is a necessary component of maintaining a suite of products that boasts a greater than 99% on-time delivery rate.
To that end, all code must be scrutinized for both stability and ease of troubleshooting and recovery.
It is not practical to discuss all of the steps that can or should be taken to write operational-quality code, but here are some things that should be considered:

* **Notification of use of backup data** [portable]
    For scripts that have a secondary data source to be used when the primary data is not available, the script must include a message that indicates the primary data is not available and backup data is being used.
    If continued use of backup data will result in a degraded product, the developer should work with NCO's SPA team to include code to notify the appropriate parties when primary data is unavailable.
    The `mail.py` utility can be useful in this regard.
* **Data of opportunity** [portable]
    It is acceptable to use data from a server or other source that is not supported 24/7.
    However, the application cannot fail when this data is missing.
    Appropriate notification must be logged indicating that the job is continuing without this data source (similar to use of backup data above).
* **Descriptive error messages** [portable]
    Fatal errors must print a descriptive message beginning with "FATAL ERROR:".
    Warnings or non-fatal error messages must be prefaced with "WARNING:".
    As with executable code, error messages in scripts must be written so that if an issue arises, the context of that error or failure is communicated as early and as clearly as possible.
* **Appropriate modes of failure** [portable]
    An executable must not terminate abnormally with a segmentation or memory fault for errors that are discoverable/trappable.
    For example, lack of input data must be handled either in the script before the executable runs, or by the executable if checking in the script is not practical.
    All scripts that depend on the existence of a certain type of input or restart data to successfully run must check for the existence of such data before running and report an informative fatal error if the needed data is missing.
* **Recovery from code failure or abnormal system failure** [portable]
    Restart capability must be applied to an operational job to save time when recovering from a failure.
    Long running jobs that have multiple executable calls might be a good candidate to break into two smaller jobs so that if a failure occurs, only the part with the problem needs to be rerun, thus the time to completion is shorter.
    An example of this would be to submit a separate post-processing job for each forecast hour, so any failure for one forecast hour does not impact others, and can be recovered from quickly.
    Any job that runs longer than 15 minutes is required to have restart capability built in such that the process picks up where it left off when rerun.
    For a forecast job, this would involve writing out checkpoint or restart files at fixed intervals during the forecast, from which the model can be restarted.
    The job scripts must be designed so this restart will happen automatically if the job is rerun.
    Any products delivered by a restarted production job must not be delayed by more than 15 minutes.
    Data assimilation jobs are exempt from this requirement, but steps should be taken to minimize runtimes and enhance re-runnability of these processes.
* **No background processing** [portable]
    `PBS Pro` loses control of processes when they are put in the background.
    Therefore, background processing must be avoided. Killing a `PBS Pro` job must terminate all processes running under it.
* **No external-pointing symlinks** [portable]
    Symbolic links to resources outside of the application directory or package (e.g. links to absolute paths) are not allowed within the package.
    When external resources are required, their paths must be obtained from production module variables (when available) or defined as variables in the version file and ecf script and used wherever the external resource is needed.
* **Working directories** [portable]
    Working directories must contain a unique identifier (job id) unless there is an application need to share the directory across multiple jobs (e.g. a forecast job writing output that is needed by a post job running in parallel).
    Working directories must be removed upon successful completion of the run.
    All data that is needed for longer than one cycle must be copied to `$COMOUT`.
    MPMD child processes must do their work in separate subdirectories of the main working directory to avoid cases where multiple processes might create/modify/remove the same file simultaneously.
* **Text formatting** [portable]
    All text files (scripts, source code, config files, etc.), as well as standard output for all jobs/scripts, must only use the basic ASCII character set, with no Windows-format carriage returns, stylized quotation marks, or other non-standard characters.
* **Documentation Blocks** [portable]
    Source code and scripts must be annotated with information that may help staff remedy a problem if something goes awry.
    In some cases, too much information is as bad as none at all.
    We ask that you use your best judgment to include information that will be of the most help in troubleshooting potential issues.
    Example 4 shows a suggested format for a documentation block (DOCBLOCK).
* **Points of contact** [portable]
    All applications running in production must have a primary and backup support contact reachable 24/7 in case of operational failures.
* **Cold starts** [portable]
    All jobs that depend on restart data from previous runs must include a cold restart option.
    Cold start is the ability to run using the current inputs and observations without any data from previous runs.
    The cold start option must be activated by the addition of "`export COLDSTART=YES`" in the job card
* **Removal of dead code** [portable]
    After initial coding updates/debugging efforts, executable statements that are made inert by commenting must be removed.
    Rely on configuration management software for content differentials.

**Example 4: DOCBLOCK template**

```text

# Program Name:
# Author(s)/Contact(s):
# Abstract:
# History Log:
#   <brief list of changes to this source file>
#
# Usage:
#  Parameters: <Specify typical arguments passed>
#  Input Files:
#    <list file names and briefly describe the data they include>
#  Output Files:
#    <list file names and briefly describe the information they include>
#
# Condition codes:
#    < list exit condition or error codes returned >
#    If appropriate, descriptive troubleshooting instructions or
#    likely causes for failures could be mentioned here with the
#    appropriate error code
#
# User controllable options: <if applicable>
```
* Use appropriate comment indicator (#, !, or //) where appropriate.

### B. Compiled Code (C or Fortran source)

> **[WCOSS]** The compiler collections, the `module load` build pattern, `FORTn` unit
> numbers, `prep_step`, and `valgrind4hpc` below are WCOSS production mechanics. The
> portable principles in this section — compile without warnings, never suppress warnings,
> fail early, descriptive errors naming the specific missing file, structured control
> instead of `GO TO` — apply everywhere.

Compiled code must be written in either C/C++ or Fortran.
C and Fortran compilers must be the latest available version of the Intel or Cray (`cc`, `CC`, and `ftn`) compiler collections.
All libraries must be approved for production use. Approved libraries are found by running `module avail` in a default environment.
Hidden modules are not allowed to be used in production.
Makefiles must only include compilers and libraries using variables defined in modules:

* Within the build script or build module in the parent sorc directory:

    ```bash

    module load cpe-cray
    module load intel/$intel_ver
    module load w3nco/$w3nco_ver
    ```
* Within the makefile:

    ```make

    LIBS = ${W3NCO_LIB4}
    ndate: ndate.f
           $(FC) –o ndate ndate.f $(LIBS)
    ```
* A build modulefile must be provided for all builds.
    See Example 11, Example 12, and Example 13 in Appendix A: Workflow Examples for an example build script, modulefile, and makefile, respectively.
* Do not specify absolute paths to executables, libraries, or any other products inside the source code or build system.
* If a module file does not provide a certain desired variable, the necessary value should be derived from the module file's contents programmatically as opposed to hardcoded (e.g., when using `bufr` module, use `"$BUFR_INC4/bufrlib.h"` not `"/lfs/h1/ops/prod/libs/intel/19.1.1.217/bufr/11.4.0/include_d/bufrlib.h"`).
* This way, if a module version is upgraded, no further modifications will be necessary for the code to compile and run with the appropriate libraries and executables.
* Code must compile without errors or warnings. Errors and warnings may not be suppressed, and the compiler warning level ("-W" options) must be at least the default one.
* Errors must be caught as early as possible and the context of the error must be communicated clearly.
* Failures must not be allowed to propagate past the point where the problem is first detectable.
* "Missing GFS data" is not an adequate error message. Indicate the specific GFS file and directory that is missing in the error message.
* Input/output errors must be handled gracefully. See available I/O control options to trap errors and add logic to allow the code to continue or fail as appropriate.
* When an executable aborts, has other problems, or needs to be tested, it is vitally important to know which disk files it uses for input and output.
* To accomplish this, the following is required:

    a) Paths of files outside a job's working directory (e.g., input data from `COMIN` or `DCOM`) must not be hard-coded in the source code, but rather defined in the calling script.
    This can be done in one of the following ways:

       * By using `FILE=var` option in the `OPEN` statement, where var is a character variable; the variable value must be exported to the shell environment before calling the executable and retrieved from the environment by either the routine `GETENV` (Fortran extension, requires "use IFPORT" in ifort) or the Fortran-2003 standard intrinsic `GET_ENVIRONMENT_VARIABLE`.
       * (An ifort extension) by omitting the `FILE=` option, in which case the file name must be set by exporting the value of the character `FORTn` variable, where n is the Fortran I/O unit number as set in the `OPEN` statement. For ifort, n is any positive integer fitting in a 4-byte variable. The production utility `prep_step` (clearing the values of all FORTn variables) must be called before each executable if this method is used.
       * By omitting the `FILE=var` option, and not setting the `FORTn` variable, in which case the default file name "fort.n" will be used by the executable. This method is allowed only if this file is a symbolic link, eg: `ln -sf $DATA/pgrbf01 fort.11`.

    b) It must be clear, by looking at the file names defined before calling the executable, which files are read from (input), written to (output), and which are both read and written within the same executable (work files).

       It can be ensured by one of the following:
          * Using numbers 11-49 for input, 51-79 for output, 80-94 for work files (preferred method for executables opening a small number of files).
          * Exporting separately the three groups of file names with appropriate headers / comments at the top of each block.

* Good programming practices must be followed to improve readability. For example, structured control must be used instead of `GO TO` statements, and code must be well documented.
* Executables should be built with production compilation settings and tested for and ridded of memory leaks/allocation problems with, e.g., `valgrind4hpc`

### C. Interpreted Code (bash, ksh, perl, or python scripts)

> **[WCOSS]** `$DATA`, `$COMROOT`, `$SENDDBN`/`$SENDDBN_NTC`, `setpdy.sh`, `prep_step` and
> `err_chk` wrapping, COMROOT cleanup, and "never write to dcom" are WCOSS mechanics. The
> portable principles — a `#!` shebang, invoke scripts directly rather than via `sh`,
> debug logging with `PS4='+ $SECONDS +'`, redirect verbose output, use the module's Python
> rather than the system's, and no false or misleading errors — apply everywhere.

Each "job" is associated with a single `J-job`, located in the `jobs` subdirectory.
The `J-job` sets up the environment and calls an `ex-script` script located in the `scripts` subdirectory.
All `J-jobs` must follow the naming convention `JAAAAA`: all capital letters beginning with the letter 'J' with no extension.
`J-jobs` must use Bash (`/bin/bash` or `/bin/sh`, the latter invokes Bash in POSIX mode on WCOSS) or Korn Shell (`/bin/ksh`).
`Ex-scripts` and utility scripts must be written in Bash, Korn shell, Perl, or Python.
`Ex-scripts` must follow the naming convention `exaaaaa.sh`: all lowercase beginning with the letters 'ex' and ending with the appropriate extension ('.sh', '.pl', '.py').
Any sub-scripts to the `ex-script` will be located in the `ush` subdirectory, be named in all lowercase letters **not** beginning with the letters 'ex,' and must end with the appropriate extension.
Underscores are permitted in all file names.

Please also observe the following points:

* Enable debug logging at the top of *each* shell script:
    ```bash

    set -x
    ```
    and add timing info to the execution trace by including the following in the J-job:
    ```bash

    export PS4='+ $SECONDS + '
    ```
* `setpdy.sh` must be called after cd to the working directory (`$DATA`)
* Utilize standard environment variables and utilities (See Standard Variables, Formats, and Utilities).
* Each block of dbnet alerts must be wrapped with logic testing whether the variable `$SENDDBN` or `$SENDDBN_NTC`, as applicable, is set to "`YES`".
* Each execution of a C or Fortran code must be wrapped with the production utilities `prep_step`, if applicable, and `err_chk`.
* Any executions that print verbose output (more than 100 lines or so per execution) must redirect standard output and standard error to a file under `$DATA`, for example:
    ```bash

    $EXECmodel/$pgm >> $pgmout 2> errfile
    ```
* Production utilizes a centralized cleanup of directories in COMROOT.
    Production scripts must not remove directories at the `$COMROOT/$NET/$ver/$RUN.$PDY` level.
* Output must conform to the output structure of `$COMROOT/$NET/$ver/$RUN.$PDY`.
* Do not assume that the current directory (".") will be in the execution path (`$PATH`).
    (Invoke temporary script as `$DATA/scriptx` or `./scriptx`).
* Model scripts and executables should be called explicitly, eg, `$USHmodel/scriptx`.
    (`$USHmodel` and `$EXECmodel` should not be added to `$PATH`).
* Remove all references to developer work areas and all development tools (benchmarking, etc.) before submitting to IDSB.
* If your application should continue if a preceding step fails, it must be documented in a comment in the script just before (or after) the relevant part is called and a descriptive "WARNING:" message printed to stdout.
* Never write to dcom! Unless you run data ingest from an outside source.
* Ensure that files containing restricted data are assigned the appropriate group and permissions.
* There must be no false/misleading errors and no syntax errors in the standard output/error file.
* Ensure all non-zero stops, aborts, calls to err_exit, etc are for good reason.
    (Eg, consider whether a bad observation should be skipped rather than causing the job to fail).
* The interpreter must be added to the top of all shell scripts with a "#!" statement.
* Shell scripts must be invoked directly (eg, "`<path_to_script>`", not "`sh <path_to_script>`").
* All packages that use Python scripts must specify a Python version through the module system, and must only call a Python executable that is from a module, not the system version.
* "`module load python/${python_ver:?}`" or similar must be present in all job files that will lead to python script calls, where the python version is defined in the version file.
* Python version must be at version 3 or higher.
* Python "FutureWarning" messages indicate that a specific feature, function, or syntax that is currently being used will be changed or removed in a future version of Python or in a future version of a Python library. Python "FutureWarning" messages are acceptable messages in operations and should not be suppressed. Developers should make an effort to resolve "FutureWarning" messages, when possible, in order to prevent production jobs from failing in the future.

Reference Appendix A: Workflow Examples for commented examples of a version file, ecFlow script, J-job, ex-script, modulefile and makefile.

## Review checklist

Items marked **[portable]** apply on RDHPCS and research code; **[WCOSS]** items apply
only to operational delivery.

- **[portable]** Fatal errors print `FATAL ERROR:`; warnings print `WARNING:`.
- **[portable]** Any job over 15 minutes has restart capability, and restarted products are
  not delayed by more than 15 minutes.
- **[portable]** No background processing; killing the job terminates all its child processes.
- **[portable]** No symlinks point outside the package (no absolute-path links).
- **[portable]** The working directory is removed on success; anything kept past one cycle is
  copied to `$COMOUT` (**[WCOSS]**) or an equivalent durable output path.
- **[portable]** Text files and standard output are ASCII-only with no carriage returns.
- **[portable]** Each source file and script carries a DOCBLOCK header.
- **[portable]** Dead (commented-out) executable statements are removed before delivery.
- **[portable]** Code compiles with no errors and no suppressed warnings; the warning level is
  at least the default.
- **[portable]** Errors are caught as early as possible and named specifically — "Missing
  GFS data" is rejected; the message names the missing file and directory.
- **[portable]** Failures do not propagate past the first point where the problem is detectable.
- **[portable]** Every production application has a primary and backup contact reachable 24/7.
- **[portable]** Jobs that depend on restart data offer a cold-start option.
- **[WCOSS]** Fortran I/O units follow 11-49 input / 51-79 output / 80-94 work, and `prep_step`
  is called before executables that use `FORTn`.
- **[WCOSS]** Each `dbn_alert` block is wrapped in a `$SENDDBN`/`$SENDDBN_NTC` check.
- **[WCOSS]** Each C or Fortran execution is wrapped with `prep_step` and `err_chk`.
- **[WCOSS]** Nothing is written to dcom unless ingesting data from an outside source.
- **[WCOSS]** Files containing restricted data carry the appropriate group and permissions.
