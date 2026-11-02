# Workflow

> **[WCOSS]** ecFlow, PBS Pro, `qsub`, job cards, and the `J-job` → `ex-script` → `ush`
> chain are the WCOSS production workflow. The portable principle: keep every
> environment-dependent setting in the job card or `J-job` — one place per variable — so
> moving from development to production changes only those exports.

## Workflow

In the production environment, all jobs are scheduled and submitted to the WCOSS resource manager, PBS Pro, by ecFlow.
EcFlow is a workflow manager developed and maintained by the European Centre for Medium-Range Weather Forecasts (ECMWF) with an intuitive GUI that is used to handle dependencies, schedule jobs, and monitor the production suite.
Each job in ecFlow is associated with an ecFlow script which gets processed to generate a `job card` (a.k.a. `submission script`) whose function is to set `PBS` (job scheduler) directives and much of the execution environment (see Standard Environment Variables) and call the `J-job` to execute processing.
The processing of the ecFlow script handles the substitution of ecFlow variables and files accessed via "%include" statements;
the resulting `job card` is then handed off to PBS Pro via `qsub`.
The purpose of the `J-job` is fourfold: to set up location (application/data directory) variables, to set up temporal (date/cycle) variables, to initialize the data and working directories, and to call the `ex-script`.
The `ex-script` is the driver for the bulk of the application, including data-staging in the working directory, setting up any model-specific variables, moving data to long-term storage, sending products off WCOSS via DBNet and performing appropriate validation and error checking.
It may call one or more `ush` (a.k.a. `utility`) scripts.
Additional discussion and examples of the workflow can be found in Appendix A: Workflow Examples.
All variables relating to the environment in which a job will run must be set, depending on the variable, within the job card or the `J-job`.
To move a model from development to production, it must only be necessary to change the variables exported in the job cards.
Downstream scripts must always use the variables established in the `J-job` and must never alter them.

Workflow Diagram:

```text
job card
  -> J-job
      -> ex-script
          -> ush
              -> utility script(s)
              -> compiled executable(s)
```

## Review checklist

- **[WCOSS]** All jobs are scheduled by ecFlow and submitted to PBS Pro via `qsub`.
- **[WCOSS]** The job card sets PBS directives and the execution environment, then calls the
  `J-job`; downstream scripts use the `J-job`'s variables and never alter them.
- **[WCOSS]** Moving a model from development to production changes only the variables
  exported in the job cards.
