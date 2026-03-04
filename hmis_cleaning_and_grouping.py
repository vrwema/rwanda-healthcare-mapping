import pandas as pd

def prepare_pfp_dataframe(
    df: pd.DataFrame,
    district_col: str = 'district',
    value_col: str = 'value',
    period_col: str = 'period',
    fy_col: str = 'FY_range'
) -> pd.DataFrame:
    """
    Clean district column, filter positive values,
    and create fiscal year range column.

    Returns a clean copy of the dataframe.
    """

    df_clean = df.copy()

    # Clean district column
    df_clean[district_col] = (
        df_clean[district_col]
        .astype(str)
        .str.replace('District', '', regex=False)
        .str.strip()
        .str.lower()
        .str.replace(' ', '', regex=False)
    )

    # Keep only rows with values > 0
    df_clean = df_clean[df_clean[value_col] > 0].copy()

    # Create FY range column
    fy_start = (
        df_clean[period_col].dt.year
        - (df_clean[period_col].dt.month < 7).astype(int)
    )

    fy_end = (
        df_clean[period_col].dt.year
        + (df_clean[period_col].dt.month >= 7).astype(int)
    ) % 100

    df_clean[fy_col] = (
        fy_start.astype(str) + '-' + fy_end.astype(str).str.zfill(2)
    )

    return df_clean



from collections.abc import Iterable


def aggregate_with_dynamic_conditions(
    df: pd.DataFrame,
    groupby_cols: list,
    value_col: str,
    conditions: dict | None = None,
    percent_definitions: list[tuple] | None = None,
    drop_zero_rows: bool = True,
    round_decimals: int = 2
) -> pd.DataFrame:
    """
    Dynamic aggregation with optional multiple percentage calculations.

    percent_definitions example:
    [
        ('anc_coverage', 'anc', 'expected_pregnancy'),
        ('first_standard_coverage', 'first_standard', 'anc'),
        ('four_standard_coverage', 'four_standard', 'anc'),
        ('eight_standard_coverage', 'eight_standard', 'anc')
    ]
    """

    df = df.copy()

    # ------------------------------
    # No conditions → simple sum
    # ------------------------------
    if not conditions:
        result = (
            df
            .groupby(groupby_cols, as_index=False)[value_col]
            .sum()
        )

        if drop_zero_rows:
            result = result[result[value_col] > 0]

        return result

    # ------------------------------
    # Conditional aggregation
    # ------------------------------
    agg_dict = {}

    for out_col, rule in conditions.items():
        cond_col = rule['column']
        cond_vals = rule['values']

        if isinstance(cond_vals, Iterable) and not isinstance(cond_vals, str):
            vals = set(cond_vals)
            agg_dict[out_col] = (
                value_col,
                lambda s, c=cond_col, v=vals:
                    s[df.loc[s.index, c].isin(v)].sum()
            )
        else:
            agg_dict[out_col] = (
                value_col,
                lambda s, c=cond_col, v=cond_vals:
                    s[df.loc[s.index, c] == v].sum()
            )

    result = (
        df
        .groupby(groupby_cols, as_index=False)
        .agg(**agg_dict)
    )

    # ------------------------------
    # Drop rows where all indicators are zero
    # ------------------------------
    if drop_zero_rows:
        result = result[result[list(conditions.keys())].sum(axis=1) > 0]

    # ------------------------------
    # Multiple percent calculations
    # ------------------------------
    if percent_definitions:
        for percent_col, num_col, denom_col in percent_definitions:

            if num_col not in result.columns or denom_col not in result.columns:
                raise ValueError(
                    f"Percent definition error: '{num_col}' or '{denom_col}' not found"
                )

            result[percent_col] = (
                result[num_col] / result[denom_col] * 100
            ).round(round_decimals)

    return result



def aggregate_indicator_with_percent(
    df,
    groupby_cols,
    indicator_col,
    value_col='value',
    filter_query=None,
    percent_name='percent',
    round_percent=1,
    sort_desc=True
):
    """
    Aggregate a single indicator and compute percent contribution.

    Parameters
    ----------
    df : pd.DataFrame
    groupby_cols : list
        Columns to group by
    indicator_col : str
        Column with 1/0 (or True/False) indicator
    value_col : str
        Numeric column to sum
    filter_query : str, optional
        Pandas query to filter dataframe
    percent_name : str
        Name of percent column
    round_percent : int
        Decimal places
    sort_desc : bool
        Sort descending by percent

    Returns
    -------
    pd.DataFrame
    """

    data = df.copy()

    if filter_query:
        data = data.query(filter_query)

    result = (
        data
        .groupby(groupby_cols)
        .apply(
            lambda g: g.loc[
                g[indicator_col].isin([1, True, '1', 'Yes']),
                value_col
            ].sum()
        )
        .reset_index(name=indicator_col)
    )

    # Keep only positive rows
    result = result[result[indicator_col] > 0]

    total = result[indicator_col].sum()

    result[percent_name] = (
        result[indicator_col] / total * 100
    ).round(round_percent)

    result = result.sort_values(
        by=percent_name,
        ascending=not sort_desc
    ).reset_index(drop=True)

    return result
