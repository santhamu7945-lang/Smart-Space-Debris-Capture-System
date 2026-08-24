import os
import requests

# -----------------------------
# CelesTrak URL (COSMOS 2251 Debris)
# -----------------------------
URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=COSMOS-2251-DEBRIS&FORMAT=TLE"

# -----------------------------
# Find the project folder
# -----------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# -----------------------------
# Create DATA/raw folder
# -----------------------------
raw_folder = os.path.join(base_dir, "DATA", "raw")
os.makedirs(raw_folder, exist_ok=True)

# -----------------------------
# File path to save
# -----------------------------
save_file = os.path.join(raw_folder, "cosmos2251.tle")

# -----------------------------
# Download dataset
# -----------------------------
try:
    response = requests.get(URL, timeout=30)

    if response.status_code == 200:
        with open(save_file, "w", encoding="utf-8") as file:
            file.write(response.text)

        print("Dataset downloaded successfully!")
        print("Saved to:")
        print(save_file)

    else:
        print("Download failed!")
        print("Status Code:", response.status_code)

except Exception as e:
    print("Error:")
    print(e)