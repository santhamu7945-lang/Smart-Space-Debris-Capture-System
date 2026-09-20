import os
import subprocess
import sys
import time
from datetime import datetime, UTC


base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

module_dir = os.path.join(
    base_dir,
    "MULTI_DEBRIS_DETECTION"
)


# =========================================================
# UPDATE INTERVALS
# =========================================================

TRACKING_UPDATE_INTERVAL_SECONDS = 60

GP_REFRESH_INTERVAL_SECONDS = 2 * 60 * 60


# =========================================================
# MODULE PATHS
# =========================================================

gp_download = os.path.join(
    module_dir,
    "download_gp_data.py"
)

state_extraction = os.path.join(
    module_dir,
    "multi_state_extraction.py"
)

proximity_filter = os.path.join(
    module_dir,
    "proximity_filter.py"
)

object_tracker = os.path.join(
    module_dir,
    "multi_object_tracker.py"
)


# =========================================================
# RUN A MODULE
# =========================================================

def run_module(module_path, module_name):

    print("\n")
    print("=" * 60)
    print(f"RUNNING: {module_name}")
    print("=" * 60)

    if not os.path.exists(module_path):

        print("\nERROR:")
        print(f"{module_name} was not found.")
        print(module_path)

        return False

    result = subprocess.run(
        [
            sys.executable,
            module_path
        ],
        cwd=module_dir
    )

    if result.returncode != 0:

        print("\nERROR:")
        print(f"{module_name} failed.")

        return False

    print(
        f"\n{module_name} completed successfully."
    )

    return True


# =========================================================
# GP DATA REFRESH
# =========================================================

def refresh_gp_data():

    print("\n")
    print("#" * 60)
    print("REFRESHING GP DATA")
    print("#" * 60)

    success = run_module(
        gp_download,
        "CelesTrak GP DATA DOWNLOAD"
    )

    if success:

        print("\nFresh GP data is now available.")

    else:

        print("\nGP data refresh failed.")
        print("Existing GP data will be used.")

    return success


# =========================================================
# TRACKING UPDATE
# =========================================================

def run_tracking_update():

    update_time = datetime.now(
        UTC
    ).isoformat()

    print("\n")
    print("#" * 60)
    print("STARTING TRACKING UPDATE")
    print("#" * 60)

    print("\nUpdate time:")
    print(update_time)


    # -----------------------------------------------------
    # 1. Calculate current state of all debris
    # -----------------------------------------------------

    success = run_module(
        state_extraction,
        "MULTI-DEBRIS STATE EXTRACTION"
    )

    if not success:
        return False


    # -----------------------------------------------------
    # 2. Apply 100 km proximity filter
    # -----------------------------------------------------

    success = run_module(
        proximity_filter,
        "100 KM PROXIMITY FILTER"
    )

    if not success:
        return False


    # -----------------------------------------------------
    # 3. Update multi-object tracking
    # -----------------------------------------------------

    success = run_module(
        object_tracker,
        "MULTI-OBJECT TRACKER"
    )

    if not success:
        return False


    completion_time = datetime.now(
        UTC
    ).isoformat()

    print("\n")
    print("=" * 60)
    print("TRACKING UPDATE COMPLETED")
    print("=" * 60)

    print("\nStarted:")
    print(update_time)

    print("\nCompleted:")
    print(completion_time)

    return True


# =========================================================
# START DYNAMIC MANAGER
# =========================================================

print("=" * 60)
print("DYNAMIC MULTI-DEBRIS UPDATE MANAGER")
print("=" * 60)

print("\nTracking update interval:")
print(
    TRACKING_UPDATE_INTERVAL_SECONDS,
    "seconds"
)

print("\nGP data refresh interval:")
print(
    GP_REFRESH_INTERVAL_SECONDS,
    "seconds"
)

print("\nPress Ctrl + C to stop.")


# =========================================================
# INITIAL GP DATA REFRESH
# =========================================================

refresh_gp_data()


# =========================================================
# INITIAL TRACKING UPDATE
# =========================================================

run_tracking_update()


# =========================================================
# START TIMERS
# =========================================================

last_gp_refresh_time = time.monotonic()

cycle_number = 2


# =========================================================
# CONTINUOUS LOOP
# =========================================================

try:

    while True:

        print("\n")
        print("=" * 60)
        print(
            f"WAITING FOR TRACKING UPDATE "
            f"{cycle_number}"
        )
        print("=" * 60)

        time.sleep(
            TRACKING_UPDATE_INTERVAL_SECONDS
        )


        # -------------------------------------------------
        # Check whether 2 hours have passed
        # -------------------------------------------------

        elapsed_time = (
            time.monotonic()
            - last_gp_refresh_time
        )


        if elapsed_time >= GP_REFRESH_INTERVAL_SECONDS:

            print("\n")
            print("#" * 60)
            print("2-HOUR GP DATA REFRESH")
            print("#" * 60)

            refresh_gp_data()

            last_gp_refresh_time = (
                time.monotonic()
            )


        # -------------------------------------------------
        # Run normal tracking update
        # -------------------------------------------------

        run_tracking_update()

        cycle_number += 1


except KeyboardInterrupt:

    print("\n")
    print("=" * 60)
    print("DYNAMIC UPDATE MANAGER STOPPED")
    print("=" * 60)

    print("\nProgram stopped by user.")