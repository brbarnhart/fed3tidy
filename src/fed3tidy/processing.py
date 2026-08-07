import polars as pl


def calc_poke_intervals(df: pl.DataFrame, active_only: bool) -> pl.DataFrame:
    if active_only:
        active_poke = df.select(pl.col("Active_Poke").first()).item()
        poke_events = [active_poke, f"{active_poke}DuringDispense"]
    else:
        poke_events = ["Left", "LeftDuringDispense", "Right", "RightDuringDispense"]

    active_intervals = df.filter(pl.col("Event").is_in(poke_events)).select(
        "Datetime",
        (pl.col("Datetime") - pl.col("Datetime").shift(1)).alias("Poke_Interval"),
    )

    return active_intervals


def calc_breakpoint(
    df: pl.DataFrame, breakpoint_cutoff: pl.Expr, active_only: bool
) -> int:

    poke_intervals = df.join(
        calc_poke_intervals(df=df, active_only=active_only), on="Datetime"
    )
    breaks = poke_intervals.filter(pl.col("Poke_Interval") >= breakpoint_cutoff)

    breakpoint: int

    if breaks.height > 0:
        breakpoint = breaks.select(pl.col("FR").first()).item()
    else:
        breakpoint = df.select(pl.col("FR").last()).item()

    return breakpoint


def summarize_data(
    df: pl.DataFrame,
    group_by_columns: list[str],
    breakpoint_cutoff: pl.Expr,
    active_only_breakpoint: bool = True,
) -> pl.DataFrame:
    # total: active pokes, inactive pokes, pellets, breakpoint
    summary = df.group_by(group_by_columns).agg(
        # *[pl.col(x).first() for x in list(set(metadata_fields) - set(group_by_cols))],
        pl.col("Active_Poke_Count").max().alias("Total_Active_Pokes"),
        pl.col("Inactive_Poke_Count").max().alias("Total_Inactive_Pokes"),
        pl.col("Pellet_Count").max().alias("Total_Pellet_Count"),
    )

    additional_columns = df.group_by(group_by_columns).map_groups(
        lambda group: pl.DataFrame(
            {
                **{col: group[col][0] for col in group_by_columns},
                "Breakpoint": calc_breakpoint(
                    group, breakpoint_cutoff, active_only=active_only_breakpoint
                ),
            }
        )
    )

    return summary.join(additional_columns, on=group_by_columns)


def bin_data(
    df: pl.DataFrame,
    group_by_columns: list[str],
    bin_length: pl.Expr,
    breakpoint_cutoff: pl.Expr,
    active_only_breakpoint: bool = True,
) -> pl.DataFrame:

    raise NotImplementedError
