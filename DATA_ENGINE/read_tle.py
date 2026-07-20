import os

# -----------------------------
# Find the TLE file
# -----------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

tle_file = os.path.join(base_dir, "DATA", "raw", "cosmos2251.tle")

# -----------------------------
# Read the file
# -----------------------------
with open(tle_file, "r", encoding="utf-8") as file:
    lines = file.readlines()

print("Total lines:", len(lines))

print("\nFirst 9 lines:\n")

for line in lines[:9]:
    print(line.strip())