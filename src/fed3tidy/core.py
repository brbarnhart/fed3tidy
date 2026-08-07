from pathlib import Path

import polars as pl


def get_raw_data_files(raw_data_path: Path) -> list[Path]:
    files = list(raw_data_path.glob("*.csv"))  # or "**/*.csv" if recursive, etc.

    if not files:
        raise ValueError(
            f"No FED3 CSV files found in '{raw_data_path}'.\n"
            "Please make sure:\n"
            "  - The folder contains at least one file ending in .csv\n"
            "  - The files follow the expected FED3 naming format (e.g. containing '_FED' or similar)\n"
        )

    return files


def get_file_metadata(path: Path, metadata_fields: list[str]) -> dict[str, str]:
    file_fields = path.stem.split("_")
    file_fields = [s.strip() for s in file_fields]

    file_fields_main = file_fields[0 : len(metadata_fields)]

    file_fields_extra = file_fields[len(metadata_fields) :]
    file_fields_extra = "_".join(file_fields_extra)

    metadata = dict(zip(metadata_fields, file_fields_main))
    metadata["Extra"] = file_fields_extra

    return metadata


def process_one_datafile(
    path: Path,
    metadata_fields: list[str],
    experiment_length: pl.Expr,
    strict_datetime: bool = True,
) -> pl.DataFrame:
    # 0) Read in the data csv
    df = pl.read_csv(path)

    # 1) Create and filter time_since_start column
    active_poke: str = df.select(pl.col("Active_Poke").first()).item()
    inactive_poke: str

    if active_poke == "Left":
        inactive_poke = "Right"
    else:
        inactive_poke = "Left"

    df = (
        df.rename(
            {
                "MM:DD:YYYY hh:mm:ss": "Datetime",
                f"{active_poke}_Poke_Count": "Active_Poke_Count",
                f"{inactive_poke}_Poke_Count": "Inactive_Poke_Count",
            }
        )
        .with_columns(
            Datetime=pl.col("Datetime").str.to_datetime(
                "%m/%d/%Y %H:%M:%S", strict=strict_datetime
            )
        )
        .with_columns(Time_Since_Start=pl.col("Datetime") - pl.col("Datetime").min())
        .filter(pl.col("Time_Since_Start") <= experiment_length)
    )

    # 2) Pull metadata out of file name
    metadata = get_file_metadata(path, metadata_fields)

    # 3) Prepend metadata to data df
    df = df.with_columns([pl.lit(value).alias(key) for key, value in metadata.items()])

    meta_cols = list(metadata.keys())
    df = df.select(meta_cols + [c for c in df.columns if c not in meta_cols])

    # 4) Return the dataframe
    return df


def create_master_df(
    data_files: list[Path],
    metadata_fields: list[str],
    experiment_length: pl.Expr,
    debug: bool = False,
    strict_datetime: bool = True,
) -> pl.DataFrame:
    df_list = []
    for file in data_files:
        if debug:
            print(file.name)

        _data = process_one_datafile(
            file, metadata_fields, experiment_length, strict_datetime
        )

        if debug:
            print(f"Shape: {_data.shape}")

        df_list.append(_data)

    master_df = pl.concat(df_list, how="vertical")

    return master_df


def load_master_df(path: Path) -> pl.DataFrame:
    return pl.read_csv(path, try_parse_dates=True)
