Some ideas for the structure of $CMD

```bash
# General api interaction:
$CMD api read endpoint [attrib] [value]
$CMD api save endpoint id attrib value
   -> how to support chaining, setting multiple attributes at once?

# For specific entities:
$CMD workunit list
$CMD workunit not-available
$CMD workunit update-status

$CMD dataset download
$CMD dataset upload

$CMD log write [workunitd] [message]

$CMD resource upload (? ideally just use app-runner functionality here?)
```

Over time, we could make the old scripts shims for the new cyclopts-based commands (this should be fairly straightforward,
in the best case all that is needed is a line in pyproject.toml and no additional script).

Very specific scripts could be kept under a common command, e.g. `protinf` but it's not clear if they should stay in
this binary long term. It would make deployment easier.
