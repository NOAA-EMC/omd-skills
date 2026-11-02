# Workflow Examples and Tables

## Appendix A: Workflow Examples

All examples are for job `jpmb_forecast`.
Model name is `nco` and type of model run is `pmb`.

**Example 5: Version file `run.ver` / `build.ver`**

The version file tracks the versions of all packages and modules used by your application.
It must not reference packages or modules that are not used.

```bash

# Description                          # Variable assignment
export nco_shared_ver=v1.0.6           # set the shared code version
export grib_util_ver=1.0.1           # set the grib_util version
```
**Example 6: Job card jpmb_forecast.ecf**

In production, ecFlow preprocesses ecFlow scripts to generate job cards that are submitted to PBS Pro.
On WCOSS, production paths are set by loading the `prod_envir` module (Example 7).
To read or write files from a development space, point the variables in your job card to the appropriate location(s).

```bash

# PBS Directives                             # Description
#PBS -N %E%pmb_forecast_00                   # job name
#PBS -A %PROJ%-%PROJENVIR%                   # project identifier
#PBS -q %QUEUE%                              # PBS Pro queue name
#PBS -S /bin/sh                              # login shell
#PBS -l walltime=01:00:00                    # wall clock
#PBS -l select=8                             # Request 8 nodes

export model=pmb

%include <head.h>                            # begin ecFlow communication
%include <envir-p1.h>                       # set up environment

export cyc=%CYC%                             # set the cycle

export MPICH_GNI_MAX_EAGER_MSG_SIZE=65536    # define parallel environment variables
export FORT_BUFFERED=TRUE

module load util_shared/$util_shared_ver    # load only modules need for this job
module load grib_util/$grib_util_ver

$HOMEpmb/jobs/JPMB_FORECAST                 # call J-job

%include <tail.h>                            # end ecFlow communication
```
**Note:**
   The `envir-phase.h` include files set the following environment variables in addition to loading the `prod_envir` and `prod_util` modules:
   `job`, `SENDDBN`, `SENDDBN_NTC`, `KEEPDATA`, `DBNROOT`, `COREROOT`, `SENDECF`, `SENDCOM`

**Example 7: prod_envir module**

To see what a module will do, run the "`module show`" or "`module display`" command.

```text

$ module display prod_envir
-------------------------------------------------------------------
   /apps/ops/prod/nco/modulefiles/prod_envir/2.0.3.lua:
-------------------------------------------------------------------
setenv("OPSROOT","/lfs/h1/ops/prod")
setenv("OPSROOTssd","/lfs/f1/ops/prod")
setenv("COMROOT","/lfs/h1/ops/prod/com")
setenv("DATAROOT","/lfs/f1/ops/prod/tmp")
setenv("DCOMROOT","/lfs/h1/ops/prod/dcom")
setenv("PACKAGEROOT","/lfs/h1/ops/prod/packages")
```
**Example 8: J-job JPMB_FORECAST**

```bash

#!/bin/sh

date                                   # print starting time
export PS4='+ $SECONDS + '              # prepend time to output
set -x                                 # enable verbose logging

export DATA=${DATA:-${DATAROOT:?}/${jobid:?}} # create temporary working directory
mkdir -p $DATA
cd $DATA

export cycle=${cycle:-t${cyc}z}          # set up temporal variables, including PDY
setpdy.sh
. ./PDY

export SENDDBN=${SENDDBN:-YES}          # alert output via DBNet
export SENDDBN_NTC=${SENDDBN_NTC:-YES}  # alert wmo output
export SENDECF=${SENDECF:-YES}          # send signals to ecFlow

export USHpmb=$HOMEpmb/ush              # sub-directories of the current model
export EXECpmb=$HOMEpmb/exec
export PARMpmb=$HOMEpmb/parm
export FIXpmb=$HOMEpmb/fix

export NET=${NET:-pmb}                  # variables used in com directory organization
export RUN=${RUN:-pmb}

export COMINgfs=${COMINgfs:-$(compath.py gfs/${gfs_ver}/gfs.$PDY)} # locations of incoming data
export COMIN=${COMIN:-$(compath.py ${NET}/${pmb_ver}/$RUN.$PDY)}

export COMOUT=${COMOUT:-$(compath.py -o ${NET}/${pmb_ver}/$RUN.$PDY)} # locations of outgoing data
export COMOUTwmo=${COMOUTwmo:-${COMOUT}/wmo}
export COMOUTgempak=${COMOUTgempak:-${COMOUT}/gempak}

mkdir –p $COMOUT $COMOUTgempak $COMOUTwmo # create output directories

export pgmout=OUTPUT.$$                 # output for executables

env                                    # print current environment

$HOMEpmb/scripts/expmb_forecast.sh     # execute ex-script
export err=$?; err_chk                 # error checking

if [ -e "$pgmout" ]; then              # print exec output
  cat $pgmout
fi

if [ "${KEEPDATA^^}" != YES ]; then    # remove temporary working directory
  rm –rf $DATA
fi

date                                   # print ending time
```
**Example 9: ex-script expmb_forecast.sh**

```bash

#!/bin/sh

# Program Name: pmb_forecast
# Author(s)/Contact(s): First Last
# Abstract: Driver script for pmb forecast
# History Log:
#   5/2014: Added error checking
#   8/2014: Modified for WCOSS
#
# Usage:
#  Parameters: None
#  Input Files:
#    pmb.tHHz.anl
#  Output Files:
#    pmb.tHHz.fFFF.grib2
#
# Condition codes:
#    99  - Missing input file
#
# User controllable options: None

set -x                                 # enable verbose logging

cpreq $COMIN/inputfile inputfile       # copy essential input files into working directory

export pgm=pmb_forecast               # name of the binary executable

. prep_step                            # clear Fortran unit assignments
export FORT11=$FIXpmb/inputfile.tbl   # set Fortran unit assignments
export FORT12=inputfile
export FORT60=outputfile.grib2

# log program start (startmsg no longer required)
mpiexec <options> $EXECmodel/$pgm >>$pgmout 2>errfile # execute MPI program
export err=$?; err_chk                 # error checking

# If multiple nodes were requested and the remainder of the job is serial processing,
# release the extra nodes to make them available to other jobs.
# See pbs_release_nodes man page for more options.
# <pbs_release_nodes -a>

if [ -s outputfile.grib2 ]; then       # check for required output
  cpfs outputfile.grib2 $COMOUT/outputfile.grib2 # copy output file to output directory
  if [ "${SENDDBN^^}" = YES ]; then    # alert output file
    $DBNROOT/bin/dbn_alert MODEL PMB_FCST \
        $job $COMOUT/outputfile.grib2
  fi
else                                   # terminate the job if the expected output cannot be found
  err_exit "outputfile.grib2 was not generated"
fi

. prep_step                            # setup for tocgrib2 exec
export FORT11=outputfile.grib2        # define input file
export FORT51=grib2.t${cyc}.z.pmb.f000 # define output file

$TOCGRIB2 <$PARMpmb/grib2_awp_pmbf000 >>$pgmout 2>errfile # add WMO header to file
if [ $? –ne 0 ]; then                  # error checking
  msg="WARNING: WMO header not added to $FORT51"
  postmsg $jlogfile "$msg"
  echo "$msg" | mail.py
fi
```
**Example 10: build readme file sorc/README**

```text

Build instructions:
cd to the sorc directory

to build all executables:
   ./build_pmb.sh

to build one or more executables, provide their name(s) as parameter(s):
   ./build_pmb.sh pmb_forecast pmb_post

to install all executables:
  ./install_pmb.sh

to clean sorc directory:
     ./clean_pmb.sh
```
**Example 11: build script sorc/build_pmb.sh**

sorc/install_pmb.sh and sorc/clean_pmb.sh are identical except replace "`make`" with "`make install`" and "`make clean`", respectively.
These scripts can be combined into a single script using arguments.

```bash

#!/bin/sh
set –x                                 # enable verbose logging

module reset
module use ../modulefiles
module load build_pmb.module

sorc_root=$PWD

function build_dir {
  cd ${sorc_root}/$1                   # move to the source directory of the given executable
  make                                 # make the executable
  if [ $? –ne 0 ]; then                # print error message if build is unsuccessful
    echo "ERROR: build of $1 FAILED!"
  fi
}

if [ $# -eq 0 ]; then                  # if no parameters were given,
  for source_dir in *.fd; do           # build all executables
    build_dir $source_dir              # enter the build_dir function
  done
else                                   # if one or more executables were requested,
  for source_dir in $*; do             # build those that were requested
    build_dir $source_dir.fd           # enter the build_dir function
  done
fi
```
**Example 12: modulefiles/build_pmb.module (to be loaded prior to compilation)**

```bash

--%Module####################################################
--                                                 First.Last@noaa.gov
--                                                 ORGANIZATION
-- PMB-FCST v1.1.0
--############################################################
-- DOCBLOCK

proc ModulesHelp { } {
  -- module help
  puts stderr "Set environment variables for PMB-FCST"
  puts stderr "This module initializes the user’s"
  puts stderr "environment to build the PMB model at NCEP"
}

-- module description
module-whatis  "PMB-FCST whatis description"

-- set version and compiler variables
set    ver v1.1.0
setenv COMP intel
setenv FC ftn

-- Load Cray parallel environment
module load  cray-mpich/$::env(cray_mpich_ver)

-- Load Intel programming environment
module load intel/$::env(intel_ver)

-- Load NCEP libs modules
-- Versions come from sourcing versions/build.ver prior to loading module
module load  hdf5/$::env(hdf5_ver)
module load  netcdf/$::env(netcdf_ver)
module load  bacio/$::env(bacio_ver)
module load  w3nco/$::env(w3nco_ver)
module load  jasper/$::env(jasper_ver)
module load  libpng/$::env(libpng_ver)
module load  zlib/$::env(zlib_ver)
```
**Example 13: sorc/pmb_forecast.fd/makefile**

```make

###############################################################
#  Makefile for xxx
#  Use:
#    make         - build the executable
#    make install - move the built executable into the exec dir
#    make clean   - start with a clean slate
###############################################################
# Makefile DOCBLOCK containing instructions and use

# Tunable parameters:
#   FC Name of the FORTRAN compiling system to use
#   LDFLAGS Options of the loader
#   FFLAGS Options of the compiler
#   DEBUG Options of the compiler included for debugging
#   LIBS List of libraries
#   CMD Name of the executable

# name of compiler
FC      = ftn
# options of the loader
LDFLAGS = -O -convert big_endian
# executable location
BINDIR  = ../../exec
# include files
INC     = ${G2_INC4}
# libraries (variables from Lmod modules)
LIBS    = ${G2_LIB4} ${W3NCO_LIB4} ${BACIO_LIB4} ${JASPER_LIB} ${PNG_LIB} ${Z_LIB}
# executable name
CMD     = pmb_forecast
# debug options
DEBUG   = -check all -ftrapuv
# compiler options
FFLAGS  = -g  -traceback  -O3 -I $(INC)

# Lines from here down should not need to be changed. They are
# the actual rules which make uses to build CMD.

OBJS = $(patsubst %.f,%.o,$(wildcard *.f))

all: $(CMD)

$(CMD): $(OBJS)
     $(FC) $(LDFLAGS) -o $(@) $(OBJS) $(LIBS)

debug: FFLAGS += $(DEBUG)
debug: all

test: $(CMD)
     $(CMD) < input.txt > output.txt
     diff output.txt valid_output.txt

install: $(CMD)
     mv $(CMD) ${BINDIR}/

clean:
     -rm -f $(OBJS) *.mod $(CMD)
```
## Appendix B: Variables and Directory Structure Tables

**Table 6: Binary executable production utilities accessible via module variables**

| Variable | exec | Description | Module |
| --- | --- | --- | --- |
| `CNVGRIB` | `cnvgrib` | Converts between GRIB1 and GRIB2 | `grib_util` |
| `COPYGB` | `copygb` | Copies all or part of GRIB1 file to another GRIB1 file | `grib_util` |
| `COPYGB2` | `copygb2` | Copies all or part of GRIB2 file to another GRIB2 file | `grib_util` |
| `DEGRIB2` | `degrib2` | Creates inventory of GRIB2 file | `grib_util` |
| `GRB2INDEX` | `grb2index` | Creates index file from GRIB2 file | `grib_util` |
| `GRBINDEX` | `grbindex` | Creates index file from GRIB1 file | `grib_util` |
| `GRIB2GRIB` | `grib2grib` | Extracts GRIB records from a GRIB file made by gribawp1 | `grib_util` |
| `TOCGRIB` | `tocgrib` | Adds WMO header in front of each GRIB1 field | `grib_util` |
| `TOCGRIB2` | `tocgrib2` | Adds WMO header in front of each GRIB2 field | `grib_util` |
| `WGRIB` | `wgrib` | Creates inventory and decodes GRIB1 files | `grib_util` |
| `WGRIB2` | `wgrib2` | Creates inventory and decodes GRIB2 files | `wgrib2` |
| `NDATE` | `ndate` | Date utility | `prod_util` |
| `MDATE` | `mdate` | Date utility | `prod_util` |
| `NHOUR` | `nhour` | Date utility | `prod_util` |
| `FSYNC` | `fsync_file` | Synchronize file across GPFS | `prod_util` |
**Table 8: Structure of sub-directories under com**

| Subdirectory | Description |
| --- | --- |
| `$COMROOT/$NET/$model_ver/$RUN.$PDY/wmo` | WMO headed output products |
| `$COMROOT/$NET/$model_ver/$RUN.$PDY/gempak` | gempak output products |
**Table 9: Structure of DCOMROOT directory**

| Subdirectory | Description |
| --- | --- |
| `$DCOMROOT/YYYYMMDD` | incoming data for one day |
| `$DCOMROOT/YYYYMM` | Incoming data for one month (select types only) |
| `$DCOMROOT/YYYYMMDD/bTTT/xxSSS` | BUFR data tanks |
*TTT* and *SSS* correspond to the 3-digit BUFR data category type and sub-type, respectively
