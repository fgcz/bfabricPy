import nox

nox.options.default_venv_backend = "uv|venv"


@nox.session
def validate_app_yml(session):
    session.install("bfabric-app-runner")
    session.run("bfabric-app-runner", "validate", "app-spec-template", "app.yml", silent=True)
