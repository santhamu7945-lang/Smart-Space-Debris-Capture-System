import os
import time
import shutil
import subprocess
from datetime import datetime

# =====================================================
# Project Base Directory
# =====================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

# =====================================================
# Existing Project Scripts
# =====================================================

DOWNLOAD_SCRIPT = os.path.join(
    BASE_DIR,
    "DATA_ENGINE",
    "download_dataset.py"
)

CLEAN_SCRIPT = os.path.join(
    BASE_DIR,
    "DATA_ENGINE",
    "clean_dataset.py"
)

FEATURE_SCRIPT = os.path.join(
    BASE_DIR,
    "DATA_ENGINE",
    "feature_extraction.py"
)

# =====================================================
# TLE Files
# =====================================================

CURRENT_TLE = os.path.join(
    BASE_DIR,
    "DATA",
    "raw",
    "cosmos2251.tle"
)

PREVIOUS_TLE = os.path.join(
    BASE_DIR,
    "DATA",
    "raw",
    "previous_cosmos2251.tle"
)

# =====================================================
# Monitoring Settings
# =====================================================

CHECK_INTERVAL = 300      # 5 minutes

# =====================================================
# Run Existing Python Script
# =====================================================

def run_script(script_path):
    """
    Executes another Python script and waits until it finishes.
    Returns True if successful, False otherwise.
    """

    print(f"\nRunning: {os.path.basename(script_path)}")

    try:

        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            print(result.stdout)

        print(f"{os.path.basename(script_path)} completed successfully.")

        return True

    except subprocess.CalledProcessError as e:

        print(f"\nError while running {os.path.basename(script_path)}")

        if e.stdout:
            print(e.stdout)

        if e.stderr:
            print(e.stderr)

        return False

    # =====================================================
# Read File Contents
# =====================================================

def file_contents(path):
    """
    Returns the contents of a file.
    Returns None if the file does not exist.
    """

    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


# =====================================================
# Compare Current TLE with Previous TLE
# =====================================================

def tle_changed():
    """
    Returns True if a new TLE is detected.
    Returns False if the TLE is unchanged.
    """

    current = file_contents(CURRENT_TLE)
    previous = file_contents(PREVIOUS_TLE)

    # First execution
    if previous is None:

        shutil.copy(
            CURRENT_TLE,
            PREVIOUS_TLE
        )

        print("First monitoring cycle.")
        print("Created previous TLE.")

        return True

    # Compare TLEs
    if current != previous:

        shutil.copy(
            CURRENT_TLE,
            PREVIOUS_TLE
        )

        print("New TLE detected.")

        return True

    print("No TLE changes detected.")

    return False

print("\n==============================================")
print(" SMART SPACE DEBRIS LIVE UPDATE MANAGER ")
print("==============================================")

# =====================================================
# Verify Required Files
# =====================================================

required_scripts = [
    DOWNLOAD_SCRIPT,
    CLEAN_SCRIPT,
    FEATURE_SCRIPT
]

print("\nVerifying required project files...")

for script in required_scripts:

    if not os.path.exists(script):

        print(f"\nERROR : {script} not found.")
        print("Update Manager cannot continue.")

        exit()

print("All required scripts found.")

# =====================================================
# Live Monitoring Loop
# =====================================================

print("\nMonitoring Started...")

while True:

    print("\n------------------------------------------")
    print("Checking for latest TLE...")
    print("Time :", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("------------------------------------------")

    # Step 1 : Download latest TLE
    if not run_script(DOWNLOAD_SCRIPT):
        print("Download failed.")
        print("Retrying after 5 minutes...")
        time.sleep(CHECK_INTERVAL)
        continue

    # Step 2 : Check whether TLE changed
    if tle_changed():

        print("\nNew TLE detected.")
        print("Updating debris database...")

        # Step 3 : Clean Dataset
        if not run_script(CLEAN_SCRIPT):
            print("Cleaning failed.")
            time.sleep(CHECK_INTERVAL)
            continue

        # Step 4 : Feature Extraction
        if not run_script(FEATURE_SCRIPT):
            print("Feature Extraction failed.")
            time.sleep(CHECK_INTERVAL)
            continue

        print("\nLatest debris_state.json generated successfully.")

    else:

        print("\nNo new TLE available.")
        print("Using existing debris_state.json")

    print(f"\nWaiting {CHECK_INTERVAL} seconds...\n")

    time.sleep(CHECK_INTERVAL)



