This document is a rough draft.

## Job Configuration Levels

One idea of the new slurm submitter is that it should become possible to merge configurations from several (but restricted)
sources. The main ones that come into account are the following ones

| Level         | Description                                                                                       |
| ------------- | ------------------------------------------------------------------------------------------------- |
| Global config | The global configuration file for the submitter provides reasonable defaults to use for all jobs. |
| App config    | The app configuration file provides default configuration that is specific to the app.            |
|               | It is also a static configuration.                                                                |
| WU config     | The workunit configuration is specific to the workunit and can be specified by the user.          |
| Dynamic/auto  | The dynamic configuration is determined by some custom logic (to be defined).                     |

### Merging operation

To keep things sane, all configs are specified as they would be config arguments of a `sbatch` command.
For each level, previous values will be replaced by this level's values.
`None` is a special value that means that the value should not be set and the argument is to be omitted, when
performing the `sbatch` command.
This allows to have a default value in the global config, and remove that parameter completely in a more specific
configuration.

This imposes the following limitations currently:

- No argument without value can be set: as far as I can tell all relevant slurm arguments come with a value always
- No argument can be specified multiple times: one where this might have been potentially necessary is the `--depend`
    flag, but even that supports passing a comma-separated list.

If either of these occurs in the future:

- The first problem could be solved by introducing a special syntax or value.
- The second problem is a bit more difficult to handle, but at least we could provide a value for some extra arguments
    which should be passed as-is, i.e. without any merging involved (or merge by concatenation).

Since neither does seem necessary right now I would propose to pick the simpler solution for now.

### Chaining jobs configuration

One case which is not handled at this level, because it would introduce a new level of complexity is chaining jobs.
The paradigm there would be that the first job gets queued with the conventional mechanism, and then it is able to chain
further jobs and submit these itself by its own logic.

One thing which might be worth exploring is how it can be made so, that the regular logic can be reused there.
