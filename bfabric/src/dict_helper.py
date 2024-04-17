def sort_dict(d: dict) -> dict:
    """
    :param d:  A dictionary
    :return:   A dictionary with items sorted by key.
       Affects how the dictionary appears, when mapped to a string
    """
    return dict(sorted(d.items()))
