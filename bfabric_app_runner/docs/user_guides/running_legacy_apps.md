# Running Legacy Apps

Compatibility shim for applications written against the old wrapper creator, which expect a
`config.yaml` in the legacy format as their sole argument. It exists so those apps can run under
app-runner without the wrapper creator, submitter and external-job machinery
([#262](https://github.com/fgcz/bfabricPy/issues/262)). Do not use it for new apps.

## The app spec

Wrapping a legacy app needs no Python: two `legacy` commands cover the whole lifecycle, and each
receives its trailing argument from the usual calling convention.

```yaml
bfabric:
  app_runner: 0.8.0
versions:
  - version:
      - 1.0.0
    commands:
      dispatch:
        type: exec
        command: >-
          bfabric-app-runner legacy dispatch
          --executable /home/bfabric/slurmworker/bin/fgcz_slurm_maxquant_linux.bash
      process:
        type: exec
        command: >-
          bfabric-app-runner legacy run
          /home/bfabric/slurmworker/bin/fgcz_slurm_maxquant_linux.bash
```

`legacy dispatch` writes a single chunk whose `inputs.yml` holds exactly one entry, the legacy YAML.
A legacy app fetches its own input resources from the scp URLs inside that YAML, so nothing else is
staged. The app's output is placed at `<chunk_dir>/output-WU<id>.zip`; use `--output-filename` for an
app whose output is not a zip.

`legacy run` invokes the app with the YAML path as its last argument, which is the convention the
legacy submitter used, with the shims described below on `PATH`. Once the app succeeds it writes the
chunk's `outputs.yml`, since a legacy app deposits its files where the YAML told it to but cannot
declare them for registration. There is deliberately no `collect` command: doing this at the end of
the process step keeps a legacy app spec to the same two commands a modern app uses, and leaves a
hand-corrected `outputs.yml` alone when you re-run `make stage`.

Both take `--config-filename` if the YAML should not be called `config.yaml`.

## The generated YAML

The resolved file has the same two sections the wrapper creator produced --- `application`
(`parameters`, `protocol`, `input`, `output`) and `job_configuration`. Resolution only reads from
B-Fabric, so it is safe to re-run `inputs prepare`, `inputs list` and `inputs check`.

Two things are deliberately absent, because app-runner already owns the state they represented.

**No external job.** `job_configuration.external_job_id` is `0`. Nothing creates an external job,
and `bfabric_setExternalJobStatus_done.py` has nothing to mark done.

**No log resources.** The wrapper creator registered a `slurm_stdout` and a `slurm_stderr` resource
on the SlurmLog storage and pointed Slurm's `-o`/`-e` at them. app-runner captures stdout and
stderr itself into a single timestamped log, so `job_configuration.stdout` and `stderr` carry
`resource_id: 0` and `url: /dev/null`, and no resource is created. The log is not reachable from
the B-Fabric UI.

Every resource id in the YAML is `0` for the same reason --- app-runner creates the output resource
during output registration, not up front. `0` rather than `null` keeps a consumer that flattens the
YAML into shell variables working under `set -u`.

To drive the input spec directly rather than through `legacy dispatch`, the entry is:

```yaml
inputs:
  - type: legacy_wrapper_yaml
    filename: config.yaml
    workunit_id: 349972
    output_path: /scratch/A224_MaxQuant/WU349972/work/output-WU349972.zip
    executable: /home/bfabric/slurmworker/bin/fgcz_slurm_maxquant_linux.bash
```

`output_path` is where the app should deposit its output, and must be an absolute path inside the
chunk directory: that makes the app's `scp` degrade to a local copy, so app-runner can register the
file afterwards. It is a spec field rather than something the resolver derives, because only the
dispatcher knows the chunk directory. `executable` overrides `job_configuration.executable`; without
it the application's own `program` field is used, which under app-runner points at the `app.yml`
rather than at the legacy app.

## The shims

For the duration of `legacy run`, a directory of shims is prepended to `PATH`.

Six are no-ops: `bfabric_setResourceStatus_available.py`,
`bfabric_setWorkunitStatus_{processing,available,failed}.py`, `bfabric_setExternalJobStatus_done.py`
and `bfabric_save_workflowstep.py`. All of them duplicate work app-runner already does, and the ids
they would be handed are sentinels, so left alone they would at best be redundant and at worst mark
the wrong entity. Neutralising `..._failed.py` loses nothing, because app-runner derives failure from
the process command's exit status: every app that calls it either exits non-zero straight afterwards
or fires it from an EXIT trap. Each shim echoes what it swallowed to stderr, which app-runner logs.

Write commands that take the *real* workunit id are deliberately left alone --- notably
`bfabric_save_workunit_attribute.py` and `bfabric_save_link_to_workunit.py`, which apps use to rename
a workunit and to attach a results link. The YAML carries the true `workunit_id`, so those calls
still do exactly what the app intends; shimming them would silently drop a user-visible feature. It
does mean the process step is not entirely free of B-Fabric writes.

`bfabric_upload_resource.py` is redirected rather than neutralised. The real command base64s the file
over SOAP, which makes B-Fabric file the resource on its own internal storage instead of the
application's. The shim instead appends the file's absolute path to `<chunk_dir>/legacy_uploads.txt`,
which `legacy run` then declares like any other output --- so a legacy app's extra resources land on
the same storage as its main output, and the internal repo stays out of it. The file is referenced
where the app left it rather than copied, since no legacy app removes its scratch directory before
exiting. A missing file is ignored rather than fatal, matching the `|| { echo failed; }` these calls
are usually wrapped in.

Because those uploads are now registered at the outputs step rather than mid-run, an app that fails
*after* uploading extra resources no longer leaves them behind in B-Fabric. In practice those calls
sit on the success path, after the main output has been written.

## What gets registered

Uploads keep the order the app made them in, and the same file is registered once however many times
it was uploaded --- including when the app uploads its declared output as well, which is one resource
rather than a name clash. `legacy_uploads.txt` is truncated at the start of each run, so a retry of
the process step never inherits the previous run's uploads.

A few legacy apps only ever upload extra resources and never write the declared output at all. If
the declared output is missing but uploads were recorded, the run warns and registers just the
uploads; if nothing at all was produced, it fails. An app that *should* have written its output fails
its own `scp` first, and a non-zero exit means no `outputs.yml` is written at all.

It also fails if a recorded upload has since disappeared, or if two *different* files would claim the
same resource name --- B-Fabric allows a resource name only once per workunit. A remote `host:path`
destination is rejected before the app starts, rather than after it has run.

## Known limitation

Most apps read the output path via `fgcz_yaml2.bash`, which uses `shyaml get-value
application.output.-1` and so passes a colon-free local path through unchanged. A few parse it
themselves and assume a `host:path` shape --- `fgcz_slurm_maxquant_textfiles.bash` does
`cut -d":" -f2`, and `fgcz_slurm_SummarizedExperiment_A315.bash` runs a `sed` expecting a
`p<number>/` segment. Those need adapting before they can run this way --- `output_path` cannot simply
be pointed at a real scp URL instead, since app-runner registers a local file and rejects a
`host:path` destination up front.
