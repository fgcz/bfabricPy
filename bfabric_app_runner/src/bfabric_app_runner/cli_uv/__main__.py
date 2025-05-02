import cyclopts

app = cyclopts.App()


# @app.default
# def dispatch():
#    pass


# @app.command
# def wheel(
#    *args: str,
#    with_: Path,
# ):
#    if with_.count(",") == 0 and with_.endswith(".whl"):
#        # extract the app ref from it.
#        pass
#
#    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
#    command = [
#        "uv",
#        "run",
#        "-p",
#        python_version,
#        "--isolated",
#        "--no-project",
#        "--with",
#        str(with_),
#        "bfabric-app-runner",
#        *args,
#        # TODO infer the package name and bind it -> this will require making it possible to inject it optionally
#        #  at top level,,
#        #  alternatively we could hack it at the end depending on the command (make it toggleable maybe)
#    ]
#
