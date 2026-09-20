import requests
from pathlib import Path

# CelesTrak SATCAT URL
URL = "https://celestrak.org/pub/satcat.csv"

# Create output folder
output_folder = Path("../DATA/raw/multi_debris")
output_folder.mkdir(parents=True, exist_ok=True)

# Output file
output_file = output_folder / "satcat.csv"

try:
    print("Downloading CelesTrak SATCAT...")

    response = requests.get(URL, timeout=30)
    response.raise_for_status()

    output_file.write_bytes(response.content)

    print("SATCAT downloaded successfully!")
    print(f"Saved to: {output_file}")

except requests.RequestException as e:
    print("Error downloading SATCAT:")
    print(e)