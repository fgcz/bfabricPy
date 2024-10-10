import nox

nox.options.default_venv_backend = "uv"


@nox.session
def tests(session):
    session.install(".[test]")
    session.run("uv", "pip", "list")
    session.run("pytest")
