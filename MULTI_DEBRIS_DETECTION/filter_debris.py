import os
import pandas as pd

# ----------------------------------
# Locate the SATCAT file
# ----------------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

satcat_file = os.path.join(
    base_dir,
    "DATA",
    "raw",
    "multi_debris",
    "satcat.csv"
)

# ----------------------------------
# Read SATCAT dataset
# ----------------------------------
df = pd.read_csv(satcat_file)

print("Total SATCAT records:", len(df))

# ----------------------------------
# Clean column names
# ----------------------------------
df.columns = df.columns.str.strip()

# ----------------------------------
# Remove completely empty rows
# ----------------------------------
df = df.dropna(how="all")

print("Records after removing empty rows:", len(df))

# ----------------------------------
# Clean important text fields
# ----------------------------------
df["OBJECT_NAME"] = df["OBJECT_NAME"].astype(str).str.strip()

df["OBJECT_TYPE"] = (
    df["OBJECT_TYPE"]
    .astype(str)
    .str.strip()
    .str.upper()
)

# ----------------------------------
# Clean NORAD IDs
# ----------------------------------
df["NORAD_CAT_ID"] = pd.to_numeric(
    df["NORAD_CAT_ID"],
    errors="coerce"
)

# ----------------------------------
# Validation
# ----------------------------------

# Remove records without a valid object name
df = df[
    df["OBJECT_NAME"].notna()
    & (df["OBJECT_NAME"] != "")
    & (df["OBJECT_NAME"] != "NAN")
]

# Remove records without a valid NORAD ID
df = df[df["NORAD_CAT_ID"].notna()]

print("Records after basic validation:", len(df))

# ----------------------------------
# Remove duplicate NORAD IDs
# ----------------------------------
before_duplicates = len(df)

df = df.drop_duplicates(
    subset=["NORAD_CAT_ID"],
    keep="first"
)

duplicates_removed = before_duplicates - len(df)

print("Duplicate NORAD records removed:", duplicates_removed)

# ----------------------------------
# Keep ONLY debris
# ----------------------------------
debris_df = df[df["OBJECT_TYPE"] == "DEB"].copy()

print("Total debris objects:", len(debris_df))

# ----------------------------------
# Create output folder
# ----------------------------------
output_folder = os.path.join(
    base_dir,
    "DATA",
    "raw",
    "multi_debris"
)

os.makedirs(output_folder, exist_ok=True)

# ----------------------------------
# Save cleaned debris catalogue
# ----------------------------------
output_file = os.path.join(
    output_folder,
    "clean_debris_satcat.csv"
)

debris_df.to_csv(
    output_file,
    index=False
)

# ----------------------------------
# Results
# ----------------------------------
print("\nCleaning & Filtering Completed")
print("Final valid debris objects:", len(debris_df))

print("\nFirst debris object:")
print(debris_df.iloc[0].to_dict())

print("\nLast debris object:")
print(debris_df.iloc[-1].to_dict())

print("\nClean debris catalogue saved successfully!")
print("Location:", output_file)