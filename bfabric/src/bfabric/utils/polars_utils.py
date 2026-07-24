import polars as pl


def flatten_relations(df: pl.DataFrame) -> pl.DataFrame:
    """Recursively flattens struct columns into individual columns, this is a bit opinionated for B-Fabric return
    values where you will often have nested structs that you want to flatten in your results.

    Each struct field becomes a column named by joining the ancestor column names and the field name with `_`, so a
    nested `b.inner.p` field becomes `b_inner_p`. All non-struct fields are kept as is.
    If there are conflicts this raises an error.
    """
    while any(isinstance(dtype, pl.Struct) for dtype in df.dtypes):
        struct_cols = [col for col, dtype in zip(df.columns, df.dtypes) if isinstance(dtype, pl.Struct)]
        flat_cols = [col for col in df.columns if col not in struct_cols]
        df = df.select(  # pyright: ignore[reportUnknownMemberType]
            flat_cols + [pl.col(col).struct.unnest().name.prefix(f"{col}_") for col in struct_cols]
        )
    return df
