# Production Utilities

> **[WCOSS]** `prep_step`, `startmsg`, `postmsg`, `err_chk`, `cpreq`, `compath.py`,
> `mail.py`, and `getsystem` are `prod_util` executables that exist only in the NCO
> production environment.
>
> **[portable]** The principles they encode apply anywhere: copy inputs into a scratch
> working directory before running, verify that every file copy succeeded, wrap each
> executable so a nonzero exit becomes a `FATAL ERROR:` and a clean job failure, and log
> a start time and progress messages to a log file (upstream notes `startmsg`/`postmsg`
> are no longer required in operations).

## C. Production Utilities

The utilities listed below must be used to assist in accomplishing certain tasks for all WCOSS models.
They are accessible through the `prod_util` module.
This module will put the below utility scripts in your environment's `PATH` and define other useful environment variables.
The module is automatically loaded in all production jobs and should be loaded in development job cards.
See Appendix A: Workflow Examples for examples of these utilities in use.

`prep_step`
  `prep_step` unsets the `FORT##` variables used to pass unit assignments to Intel Fortran executables.
  Since there may be multiple Fortran programs running in a job, these variables must be reset before each program execution.

`startmsg` *
  `startmsg` posts the start time of a program to `stdout`.

`postmsg` *
  `postmsg` writes a message to a log file.
  The first argument is the log file name and the second is the message.
  The log file will default to stdout.

\* startmsg and postmsg are no longer required in operations but the utilities will continue to be maintained.

`err_chk` / `err_exit`
  It is imperative that all production code and scripts broadly employ error checking to catch and recover from errors as quickly as possible.
  The context of the error must be communicated as descriptively as possible and prefaced with "WARNING:" or "FATAL ERROR:".
  Failures must not be allowed to propagate downstream of the point where the problem can first be detected;
  jobs should fail with `err_chk` or `err_exit` as soon as a fatal error is encountered.
  `err_chk` is used to check and handle the `$err` variable which has been set to a program's return code and exported into the environment.
  If `$err=0`, err_chk does nothing and job execution continues.
  If `$err` is non-zero, the job is aborted.
  `err_exit` will write an error message with the time of the error, and immediately abort the job in PBS Pro.
  It accepts an error string as input to which it will prepend "FATAL ERROR."

`cpreq`
  `cpreq` is used to copy files that are essential to an application.
  If the copy is unsuccessful for any reason, then a FATAL ERROR will be printed and the job will abort immediately.
  It has the same usage as the standard `cp` command.

`cpfs`
  `cpfs` is used to copy files while ensuring that the whole file has been copied before it becomes accessible so that downstream applications will not attempt to copy or read a partial file.
  It has the same usage as the standard `cp` command with the limitation that it may only copy one file at a time (no globbing).
  It is most useful for copies across file systems or for very large files.
  `cpfs $COMIN/$file $new_file` will execute the following:

  ```bash

  cpreq $COMIN/$file $new_file.cptmp
  $FSYNC $new_file.cptmp
  mv $new_file.cptmp $new_file
  ```
  `cpfs` calls the `err_exit` utility if either the cp or mv step returns non-zero status.
  However, as a further check, verify that a source file exists before calling `cpfs`.
  If the job should continue without the file, skip the `cpfs` call and continue.
  If the job should fail if the source file does not exist, call err_exit directly.

`compath.py`
  The `compath.py` utility is used to discover the current absolute path of a given `com` directory and is used to set COMIN and COMOUT variables in `J-jobs`.
  `compath.py` accepts the relative path of the directory you wish to use data from as an argument;
  the corresponding absolute path is returned:

  ```bash

  COMIN=${COMIN:-$(compath.py $envir/$NET/$model_ver/$RUN.$PDY)}
  COMINm1=${COMINm1:-$(compath.py $envir/$NET/$model_ver/$RUN.$PDYm1)}
  COMINgfs=${COMINgfs:-$(compath.py $envir/gfs/$gfs_ver/gfs.$PDY)}
  COMOUT=${COMOUT:-$(compath.py -o $NET/$model_ver/$RUN.$PDY)}
  ```
  Run `compath.py --help` to see all usage options.
  To use non-production data, in the job card set the `$COMPATH` environment variable to a list of absolute paths.
  `compath.py` will search those paths for a match before defaulting to production data.
  Example: `export COMPATH="$COMROOT/nco:/dev/noscrub/First.Last/prod/com/gfs"`

`mail.py`
  When nonfatal errors occur that may impact the quality of the model output, such as when backup data is used, it is important to notify the appropriate parties so that the error can be addressed.
  The `mail.py` utility is used to send an e-mail notification from any node on the system.
  To notify production staff of a nonfatal but significant issue with a production job, one might execute:

  ```bash

  msg="WARNING: Primary data source unavailable. Backup data is being used."
  echo "$msg" | mail.py
  ```
  An addressee list can be included on the command line or set in advance via environment variable `$MAILTO`.
  To copy someone, use the "-c" flag:

  ```bash

  echo "$msg" | mail.py –c <someones_email_address>
  ```
  Run `mail.py -h` after loading the `prod_util` module to see additional options.
  Note that e-mail is only sent in jobs run by NCO.
  Jobs run by others will merely print the message to stdout.

`getsystem`
  `getsystem` simply tells you which WCOSS system you are on.
  This utility exists for command line execution and must not be used in any operational packages.
  Table 2 shows what you can expect to receive when running this utility on a given system with a given set of option flags:

**Table 2: getsystem output**

| System | no flags | -p |
| --- | --- | --- |
| Dogwood phase 1 | Dogwood | Dogwood-p1 |
| Cactus phase 1 | Cactus | Cactus-p1 |

## Review checklist

- **[WCOSS]** Call `prep_step` before each executable that reads `FORTn` units, and `err_chk`
  after each executable to trap a nonzero exit.
- **[WCOSS]** Use `cpreq` rather than `cp` for file copies so a failed copy is fatal.
- **[WCOSS]** Use `compath.py` to resolve COM paths and `mail.py` for notifications instead of
  hardcoding paths or calling `mail` directly.
- **[portable]** Every external command's exit status is checked; failures are never silently
  swallowed.
