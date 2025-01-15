import polars as pl


def flatten_relations(df: pl.DataFrame) -> pl.DataFrame:
    """Flattens relations inside of the dataframe into individual columns, this is a bit opinionated for B-Fabric return
    values where you will often have a struct (1 level deep) that you want to flatten in your results.

    The columns of the new values will be the original column name with `_` and the field name appended.
    All non-struct fields will be kept as is.
    If there are conflicts this raises an error.
    """
    struct_cols = [col for col, dtype in zip(df.columns, df.dtypes) if isinstance(dtype, pl.Struct)]
    flat_cols = [col for col in df.columns if col not in struct_cols]
    return df.select(flat_cols + [pl.col(col).struct.unnest().name.prefix(f"{col}_") for col in struct_cols])
