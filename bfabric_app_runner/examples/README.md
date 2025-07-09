How i am testing it.
Picked an internal workunit for testing purposes.

```bash
uvx copier copy ~/code/bfabricPy/bfabric_app_runner/examples/template hello1
# entered "hello1" as project name (but it could be changed)

cd hello1
bash release.bash
cd ..

uvx -p 3.13 bfabric-app-runner prepare workunit hello1/app.yml --work-dir workdir --workunit-ref 328722 --read-only --force-app-version 0.0.1
cd workdir

```
