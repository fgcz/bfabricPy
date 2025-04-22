def is_excel_available() -> bool:
    """Checks if `excel` support is available."""
    try:
        import fastexcel

        return True
    except ImportError:
        return False


def decorate_if_excel(decorator):
    """Returns a decorator which applies the wrapped `decorator` only if `excel` support is available."""
    if is_excel_available():

        def dec(func):
            return decorator(func)

    else:

        def dec(func):
            return func

    return dec
