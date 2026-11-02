# File Name Conventions

## B. File Name Conventions

Standard file naming conventions must also be used.
File names must not contain special characters, uppercase characters or the date (the directory in which the file resides will contain the date).
File names must indicate the name of the model run, the cycle, the type of data the file contains, the resolution of the data (if applicable), other data related elements, the three-digit forecast hour the data represents (if applicable), and the file type.
Please adhere to the following:

* For all model types:
    * Use periods to separate categories and use underscores to separate words within the same category
    * Use a "p" in describing a "point" within a grid resolution. Ex. 0.25 = `0p25`
    * Use a leading 0 in describing a grid resolution that is less than 1.
    * Include an "f" in front of the forecast hour
    * Pad forecast hours with zeros so that all files have the same number of digits
    * In cases where there is no forecast hour, but rather it is output that is before the cycle time, "tm" may be substituted for "f" in the filename.
    * `domain` does not need to be included in the filename if there is only one domain used by the model
    * ASCII inventory files (output of wgrib/wgrib2) should end with the extension ".grib2.idx". Ex. `hrrr.t10z.wrfnatf01.grib2.idx`
    * Other index files (in binary format) should end with the extension ".bin.idx"
    * If `var_info` includes multiple pieces of information, they should be separated with a period. This includes resolution if there are multiple resolutions produced. Ex. `gefs.t06z.avg.pres_a.0p50.f006.grib2`, `etss.t00z.stormsurge.2p5km.conus.grib2`
* Output file names must be consistent across environments and application versions, so variables such as `$job`, `$envir`, and `$model_ver` must not be used to define file names.
* Public products can be produced in any of the following formats: netcdf, bufr, grib2, ascii
* If the directory structure includes the cycle, it should be a subdirectory. `<model>.YYYYMMDD/HH/`
* For coupled models in particular:
    * Output directory structure should have subdirectories for each model component Ex. `gefs.YYYYMMDD/HH/atmos/`

Filename format for files in `com`:

* non-ensemble: atmospheric, hydro models: `model.tHHz.var_info.f###.domain.format`
* ensemble: atmospheric, hydro models: `model.tHHz.ens_mem.var_info.f###.domain.format`
* non-ensemble: coupled models: `model.component.tHHz.var_info.f###.domain.format`
* ensemble: coupled models: `model.component.tHHz.ens_mem.var_info.f###.domain.format`
* hurricane models: `model.tHHz.storm_name.var_info.f###.domain.format`
* space weather models: `model.var_info.valid_time.domain.format`

Example filenames for files in `com` ( `HH` is the cycle/hour):

* `rtofs_glo.tHHz.std.f180.west_conus.grib2`
* `aqm.tHHz.8hr_o3.227.grib2` (227 is the domain in this case)
* `sref.tHHz.pgrb216.p10_3hrly.grib2.idx` → `sref.tHHz.p10.pres_3hrly.216.grib2.idx`
* `gefs.chem.tHHz.a2d_0p25.f###.grib2` → `gefs.chem.tHHz.a2d.0p25.f###.grib2`

Filename format for files in the `wmo` sub-directory: `format.model.tHHz.awp_var_info.f###.domain`

Example filenames for files in the wmo sub-directory:

* `grib2.aqm.tHHz.08hr_o3.227`
* `grib2.akrtma.tHHz.2dvaranl.198`
* `grib2.sref.tHHz.spread.212`
