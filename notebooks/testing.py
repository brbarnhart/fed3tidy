# %%
from pathlib import Path

import polars as pl

from fed3tidy import *

# %%
proj_dir = Path("..")
data_dir = proj_dir / "sample_data"

# %%
data_files = get_raw_data_files(data_dir)

# %%
print(data_files[0].stem.split("_"))
# %%
metadata_fields = ["ID", "Sex", "Stim", "Diet", "Cohort"]

df = create_master_df(data_files, metadata_fields, pl.duration(minutes=30))

# %%
grouping_cols = ["ID", "Stim", "Diet"]
print(summarize_data(df, metadata_fields, pl.duration(minutes=30)))


# %%
print(summarize_data(df, metadata_fields, pl.duration(minutes=30)).columns)
