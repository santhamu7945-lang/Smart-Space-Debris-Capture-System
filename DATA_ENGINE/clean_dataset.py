import os
import json

# ----------------------------------
# Locate the TLE file
# ----------------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tle_file = os.path.join(base_dir, "DATA", "raw", "cosmos2251.tle")

# ----------------------------------
# Read the file and remove blank lines
# ----------------------------------
with open(tle_file, "r", encoding="utf-8") as file:
    lines = [line.strip() for line in file if line.strip()]

print("Total lines after removing blank lines:", len(lines))

# ----------------------------------
# Clean and Filter the dataset
# ----------------------------------
clean_data = []
seen_norad = set()

for i in range(0, len(lines), 3):

    # Check if all three lines exist
    if i + 2 >= len(lines):
        continue

    name = lines[i]
    line1 = lines[i + 1]
    line2 = lines[i + 2]

    # ----------------------------------
    # Validation
    # ----------------------------------

    # Name should not be empty
    if not name:
        continue

    # Line 1 should start with "1 "
    if not line1.startswith("1 "):
        continue

    # Line 2 should start with "2 "
    if not line2.startswith("2 "):
        continue

    # Extract NORAD ID
    norad_id = line1[2:7].strip()

    # Remove duplicate objects
    if norad_id in seen_norad:
        continue

    seen_norad.add(norad_id)

    clean_data.append({
        "name": name,
        "norad_id": norad_id,
        "line1": line1,
        "line2": line2
    })

# ----------------------------------
# Create processed folder
# ----------------------------------
processed_folder = os.path.join(base_dir, "DATA", "processed")
os.makedirs(processed_folder, exist_ok=True)

# ----------------------------------
# Save cleaned data
# ----------------------------------
output_file = os.path.join(processed_folder, "clean_debris.json")

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(clean_data, file, indent=4)

# ----------------------------------
# Results
# ----------------------------------
print("\nCleaning & Filtering Completed")
print("Total Valid Objects:", len(clean_data))

print("\nFirst Object:")
print(clean_data[0])

print("\nLast Object:")
print(clean_data[-1])

print("\nClean dataset saved successfully!")
print("Location:", output_file)