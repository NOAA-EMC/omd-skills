# Dataflow

## Dataflow

Distributed Brokered Networking (DBNet) is used to disseminate products operationally from WCOSS.
DBNet is a series of server/client daemons that are controlled by table and key relationships.
To disseminate a product, jobs running on WCOSS make a call to the `dbn_alert` executable which makes the DBNet software aware of the new product.
Then, based on entries in several different tables, the product can be sent to one or more external servers.
The NCO Dataflow Team is responsible for maintaining DBNet. Any alert that is new or changing needs to be coordinated with the Dataflow Team so that the product will continue to go to all of the external customers specified in the governing tables.
All DBNet alerts must be wrapped in a check for `$SENDDBN` (or `$SENDDBN_NTC`) equal to "`YES`".
Example call:

```bash

$DBNROOT/bin/dbn_alert MODEL PMB_GB2 $job $COMOUT/$outputfile
```
**DBN Alert Fields**

| Field | Description |
| --- | --- |
| Type [ `MODEL` ] | Generic data type |
| Subtype [ `PMB_GB2` ] | Specific data type under the generic type |
| Job Name [ `$job` ] | Name of the process that alerted the file, this is only used in the log output. It can be helpful when trying to identify the job that called `dbn_alert` |
| File [ `$COMOUT/$outputfile` ] | File to be alerted; must include the full path. |
