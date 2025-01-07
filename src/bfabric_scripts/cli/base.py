import functools
import inspect
from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging


def use_client(fn, setup_logging: bool = True):
    """Decorator that injects a Bfabric client into a function.

    The client is automatically created using default configuration if not provided.
    If setup_logging is True (default), logging is set up using setup_script_logging.
    """
    # Get the original signature
    sig = inspect.signature(fn)

    # Create new parameters without the client parameter
    params = [param for name, param in sig.parameters.items() if name != "client"]

    # Create a new signature without the client parameter
    new_sig = sig.replace(parameters=params)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if setup_logging:
            setup_script_logging()
        if "client" in kwargs:
            client = kwargs.pop("client")
        else:
            client = Bfabric.from_config()
        return fn(*args, **kwargs, client=client)

    # Update the signature of the wrapper
    wrapper.__signature__ = new_sig
    return wrapper
