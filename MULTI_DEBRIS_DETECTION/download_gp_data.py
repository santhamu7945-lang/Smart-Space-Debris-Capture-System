import os
import requests
import pandas as pd
from io import StringIO

# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

satcat_file = os.path.join(
    base_dir,
    "DATA",
    "raw",
    "multi_debris",
    "clean_debris_satcat.csv"
)

output_file = os.path.join(
    base_dir,
    "DATA",
    "raw",
    "multi_debris",
    "gp_data.csv"
)


# ---------------------------------------------------------
# READ CLEAN DEBRIS CATALOGUE
# ---------------------------------------------------------

satcat_df = pd.read_csv(satcat_file)

print("Total debris in SATCAT:", len(satcat_df))


# ---------------------------------------------------------
# KEEP ONLY NON-DECAYED DEBRIS
# ---------------------------------------------------------

satcat_df["DECAY_DATE"] = (
    satcat_df["DECAY_DATE"]
    .fillna("")
    .astype(str)
    .str.strip()
)

non_decayed_df = satcat_df[
    satcat_df["DECAY_DATE"] == ""
].copy()

print(
    "Non-decayed debris in SATCAT:",
    len(non_decayed_df)
)


# ---------------------------------------------------------
# DOWNLOAD CURRENT GP DATA
# ---------------------------------------------------------

url = (
    "https://celestrak.org/NORAD/elements/"
    "gp.php?NAME=DEB&FORMAT=CSV"
)

print("\nDownloading current debris GP data...")

try:

    response = requests.get(
        url,
        timeout=60
    )

except requests.RequestException as error:

    print("Request failed:", error)
    raise SystemExit


# ---------------------------------------------------------
# CHECK RESPONSE
# ---------------------------------------------------------

print("HTTP status:", response.status_code)

if response.status_code != 200:

    print("GP download failed.")
    print("Response:")
    print(response.text[:500])

    raise SystemExit


text = response.text.strip()

if not text.startswith("OBJECT_NAME"):

    print("Invalid GP response received.")
    print(text[:500])

    raise SystemExit


# ---------------------------------------------------------
# READ GP CSV
# ---------------------------------------------------------

gp_df = pd.read_csv(
    StringIO(text)
)

print(
    "Total GP records received:",
    len(gp_df)
)


# ---------------------------------------------------------
# CLEAN NORAD IDs
# ---------------------------------------------------------

gp_df["NORAD_CAT_ID"] = pd.to_numeric(
    gp_df["NORAD_CAT_ID"],
    errors="coerce"
)

gp_df = gp_df[
    gp_df["NORAD_CAT_ID"].notna()
].copy()

gp_df["NORAD_CAT_ID"] = (
    gp_df["NORAD_CAT_ID"]
    .astype(int)
)


# ---------------------------------------------------------
# MATCH GP DATA WITH NON-DECAYED SATCAT DEBRIS
# ---------------------------------------------------------

non_decayed_df["NORAD_CAT_ID"] = pd.to_numeric(
    non_decayed_df["NORAD_CAT_ID"],
    errors="coerce"
)

non_decayed_df = non_decayed_df[
    non_decayed_df["NORAD_CAT_ID"].notna()
].copy()

non_decayed_df["NORAD_CAT_ID"] = (
    non_decayed_df["NORAD_CAT_ID"]
    .astype(int)
)


matched_gp_df = gp_df[
    gp_df["NORAD_CAT_ID"].isin(
        non_decayed_df["NORAD_CAT_ID"]
    )
].copy()


# ---------------------------------------------------------
# REMOVE DUPLICATES
# ---------------------------------------------------------

matched_gp_df = matched_gp_df.drop_duplicates(
    subset=["NORAD_CAT_ID"],
    keep="first"
)


# ---------------------------------------------------------
# SAVE RESULT
# ---------------------------------------------------------

matched_gp_df.to_csv(
    output_file,
    index=False
)


# ---------------------------------------------------------
# FINAL REPORT
# ---------------------------------------------------------

print("\n========================================")
print("GP DOWNLOAD COMPLETED")
print("========================================")

print(
    "Non-decayed SATCAT debris:",
    len(non_decayed_df)
)

print(
    "GP records received:",
    len(gp_df)
)

print(
    "Matching non-decayed debris with GP:",
    len(matched_gp_df)
)

print(
    "\nGP data saved to:"
)

print(output_file)