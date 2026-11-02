# Date and GRIB Utilities

> **[WCOSS]** `finddate.sh`, `ndate`, and `setpdy.sh` come from the `prod_util` module; the
> GRIB tools come from `grib_util` and `wgrib2`. These are NCO production utilities. The
> portable principle: never compute date arithmetic or parse GRIB inline — call the
> documented utility so behavior is identical across jobs and correct at year boundaries.

## D. Date Utilities

The following utilities are used to manage dates in the production suite.
They must be used wherever current dates are employed to enable proper scheduling and ensure that all jobs work as expected when crossing over to a new year.
The following date utilities are accessed by loading the `prod_util` module.

`finddate.sh`
  Given a date, `finddate.sh` will return a date (in `YYYYMMDD` format) a specified number of days before or after the given date.
  It may also provide a sequence of dates leading to the specified number of days before or after the given date.
  Example 1 shows how to use `finddate.sh`.

**Example 1: Using finddate.sh**

```bash

#!/bin/sh
module load prod_util/$prod_util_ver

PDY=20220101

# Single date example
ten_days_ago=$(finddate.sh $PDY d-10)
ten_days_ahead=$(finddate.sh $PDY d+10)

# Sequence example
last_four_days=$(finddate.sh $PDY s-4)
next_four_days=$(finddate.sh $PDY s+4)

echo "Today's date is $PDY"
echo "The date ten days ago was $ten_days_ago"
echo "The date in ten days will be $ten_days_ahead"
echo "The last four days were $last_four_days"
echo "The next four days are $next_four_days"
```
**Output**

```text

Today's date is 20220101
The date ten days ago was 20211222
The date in ten days will be 20220111
The last four days were 20211231 20211230 20211229 20211228
The next four days are 20220102 20220103 20220104 20220105
```
`ndate`
  `ndate` is accessible by the variable `$NDATE` once the `prod_util` module has been loaded.
  `ndate` is a date utility that will return a date in YYYYMMDDHH format.
  Given no arguments, it will return the current date/hour. `ndate` takes up to two arguments, namely `fhour` and `idate`: `ndate [fhour [idate]]`.
  `fhour` is a forecast hour (may be negative) and defaults to zero.
  `idate` is the initial date in YYYYMMDDHH format and defaults to the current date.
  Example 2 shows how to use `ndate`.

**Example 2: Using ndate**

```bash

#!/bin/sh
module load prod_util/$prod_util_ver

PDYHH=$($NDATE)

# Single date example
ten_days_ago=$($NDATE -240 $PDYHH)
ten_days_ahead=$($NDATE 240 $PDYHH)

# cycle examples
next_cycle=$($NDATE 06 $PDYHH)
prev_cycle=$($NDATE -06 $PDYHH)

echo "Today's date and cycle is $PDYHH"
echo "The date ten days ago was $ten_days_ago"
echo "The date in ten days will be $ten_days_ahead"
echo "Six hours from now will be $next_cycle"
echo "Six hours ago was $prev_cycle"
```
**Output**

```text

Today's date and cycle is 2022010112
The date ten days ago was 2021122212
The date in ten days will be 2022011112
Six hours from now will be 2022010118
Six hours ago was 2022010106
```
`setpdy.sh`
  `setpdy.sh` creates a file `PDY` that is sourced to export the standard date variables `PDYmnm`, `PDYm{nm-1}`, ..., `PDYm2`, `PDYm1`, `PDY`, `PDYp1`, `PDYp2`, ..., `PDYp{np-1}`, `PDYpnp`.
  By default, `nm` and `np` are 7 but can be altered by providing alternate numbers as input parameters.
  The variable `cycle` must be set (in 'tHHz' format) prior to execution.
  The default date is the current day's date as defined in the file `$COMDATEROOT/date/$cycle`, but it can be overridden by setting the variable `PDY` prior to execution.
  The date files in `$COMDATEROOT/date` are set at 11:30 UTC and 23:30 UTC.
  At 23:30, the date files for cycles 00-11 are incremented to the next day.
  At 11:30, the date files for cycles 12-23 are likewise advanced.
  Therefore, if you were to set `cycle` to t12z and run `setpdy.sh` between 00:00 and 11:30, you would get a PDY file centered on the previous day's date (unless variable `PDY` was imported). Example 3 shows how to use `setpdy.sh`.

**Example 3: Using setpdy.sh (assuming current date is 20160101)**

```bash

#!/bin/sh
module load prod_util/$prod_util_ver
export cycle=t12z

setpdy.sh 8 3
. ./PDY

echo "Yesterday's date was $PDYm1"
```
**Contents of file PDY**

```bash

export PDYm8=20151224
export PDYm7=20151225
export PDYm6=20151226
export PDYm5=20151227
export PDYm4=20151228
export PDYm3=20151229
export PDYm2=20151230
export PDYm1=20151231
export PDY=20160101
export PDYp1=20160102
export PDYp2=20160103
export PDYp3=20160104
```
**Output**

```text

Yesterday's date was 20151231
```
## E. GRIB Utilities

GRIB is a data format commonly used across the production model suite at NCEP and in Numerical Weather Prediction worldwide.
NCO supports several utilities responsible for manipulating GRIB data. These utilities are accessible in production via the `grib_util` and `wgrib2` modules.
The module will define numerous environment variables. See Table 6 (in Appendix B: Variables and Directory Structure Tables) for all variable definitions and descriptions of each utility.
The module must be loaded in the job cards of jobs using GRIB utilities:

```bash

module load grib_util/$grib_util_ver
module load wgrib2/$wgrib2_ver
```

## Review checklist

- **[WCOSS]** Use `finddate.sh`, `ndate`, and `setpdy.sh` for date arithmetic; do not hand-roll
  date math that breaks when crossing into a new year.
- **[WCOSS]** Use `wgrib2` (or the approved GRIB utility) for GRIB inspection and subsetting
  rather than ad-hoc parsing.
