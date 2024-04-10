

def div_int_ceil(n: int, d: int) -> int:
    """
    :param n: Numerator
    :param d: Denominator
    :return:  Performs integer ceiling division
    Theoretically equivalent to math.ceil(n/d), but not subject to floating-point errors.
    """
    q, r = divmod(n, d)
    return q + bool(r)



if __name__ == "__main__":
    print(
        div_int_ceil(120, 100),
        div_int_ceil(200, 100),
        div_int_ceil(245, 100)
    )