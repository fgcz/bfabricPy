import functools

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging


def use_client(fn, setup_logging: bool = True):
    """Decorator that injects a Bfabric client into a function.

    The function must have a `client` keyword argument.
    If the function is called without a `client` keyword argument, a client is created using the default configuration.
    If `setup_logging` is True (default), the logging is set up using `setup_script_logging`.
    """
    fn_for_sig = functools.partial(fn, client=None)

    @functools.wraps(fn_for_sig)
    def wrapper(*args, **kwargs):
        if "client" in kwargs:
            client = kwargs.pop("client")
        else:
            client = Bfabric.from_config()
        if setup_logging:
            setup_script_logging()
        return fn(*args, **kwargs, client=client)

    return wrapper
