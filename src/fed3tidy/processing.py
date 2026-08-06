import polars as pl


def calc_poke_intervals(df: pl.DataFrame, active_only: bool) -> pl.DataFrame:
    if active_only:
        active_poke = df.select(pl.col("Active_Poke").first()).item()
        poke_events = [active_poke, f"{active_poke}DuringDispense"]
    else:
        poke_events = ["Left", "LeftDuringDispense", "Right", "RightDuringDispense"]

    active_intervals = df.filter(pl.col("Event").is_in(poke_events)).select(
        "datetime",
        (pl.col("datetime") - pl.col("datetime").shift(1)).alias("poke_interval"),
    )

    return active_intervals


def calc_breakpoint(
    df: pl.DataFrame, breakpoint_cutoff: pl.Expr, active_only: bool
) -> int:

    poke_intervals = df.join(
        calc_poke_intervals(df=df, active_only=active_only), on="datetime"
    )
    breaks = poke_intervals.filter(pl.col("poke_interval") >= breakpoint_cutoff)

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

    active_poke: str = df.select(pl.col("Active_Poke").first()).item()
    inactive_poke: str

    if active_poke == "Left":
        inactive_poke = "Right"
    else:
        inactive_poke = "Left"

    # total: active pokes, inactive pokes, pellets, breakpoint
    summary = df.group_by(group_by_columns).agg(
        # *[pl.col(x).first() for x in list(set(metadata_fields) - set(group_by_cols))],
        pl.col(f"{active_poke}_Poke_Count").max().alias("active_pokes"),
        pl.col(f"{inactive_poke}_Poke_Count").max().alias("inactive_pokes"),
        pl.col("Pellet_Count").max().alias("pellet_count"),
    )

    additional_columns = df.group_by(group_by_columns).map_groups(
        lambda group: pl.DataFrame(
            {
                **{col: group[col][0] for col in group_by_columns},
                "breakpoint": calc_breakpoint(
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
