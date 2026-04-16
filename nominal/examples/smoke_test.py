"""Smoke test: connect to Moonraker, query printer objects, and exit.

Set NOMINAL_API_KEY in the environment and pass a dataset RID to also test publishing.

Usage:
    uv run python examples/smoke_test.py
    uv run python examples/smoke_test.py <dataset_rid>
    NOMINAL_API_KEY=your_key uv run python examples/smoke_test.py <dataset_rid>
"""

import os
import sys
import time

from nominal_moonraker import NominalMoonraker

DATASET_RID = sys.argv[1] if len(sys.argv) > 1 else None
NOMINAL_API_KEY = os.environ.get("NOMINAL_API_KEY")

printer = NominalMoonraker(name="myPrinter", host="localhost", port=7125)

if DATASET_RID:
    from nominal_instro.lib.publishers import NominalCorePublisher

    publisher = NominalCorePublisher(dataset_rid=DATASET_RID, api_key=NOMINAL_API_KEY)
    printer.add_publisher(publisher)
    print(f"Publishing to Nominal Core dataset: {DATASET_RID}")

printer.open()

try:
    # List available printer objects
    objects = printer.list_printer_objects()
    print(f"Available objects ({len(objects)}): {', '.join(objects[:10])}...")

    # Query subsystems via generic describe()
    for obj in ["toolhead", "motion_report", "gcode_move", "extruder", "heater_bed",
                 "print_stats", "fan", "virtual_sdcard", "idle_timeout"]:
        try:
            m = printer.describe(obj)
            print(f"{obj}: {list(m.channel_data.keys())}")
        except Exception as e:
            print(f"{obj}: {e}")

    # Start subscription-based background worker
    printer.background_interval = 1.0
    printer.start()
    time.sleep(3)

    # Scalar fields (unchanged naming)
    bed_temp = printer.get_channel("myPrinter.heater_bed.temperature", 1, True)
    ext_temp = printer.get_channel("myPrinter.extruder.temperature", 1, True)

    # Indexed fields now use named suffixes from PrinterObject.index_names
    # e.g. position[0] -> position.x, live_velocity is a scalar field
    velocity = printer.get_channel("myPrinter.motion_report.live_velocity", 1, True)

    print(f"\nBackground subscription results:")
    print(f"  Bed temp: {bed_temp.latest}")
    print(f"  Extruder temp: {ext_temp.latest}")
    print(f"  Live velocity: {velocity.latest}")

    print("\nSmoke test passed.")

finally:
    printer.close()
