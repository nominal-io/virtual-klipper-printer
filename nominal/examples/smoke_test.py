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

    # Query each subsystem
    toolhead = printer.describe_toolhead()
    print(f"Toolhead channels: {list(toolhead.channel_data.keys())}")

    extruder = printer.describe_extruder()
    print(f"Extruder channels: {list(extruder.channel_data.keys())}")

    bed = printer.describe_heater_bed()
    print(f"Heater bed channels: {list(bed.channel_data.keys())}")

    stats = printer.describe_print_stats()
    print(f"Print stats channels: {list(stats.channel_data.keys())}")

    fan = printer.describe_fan()
    print(f"Fan channels: {list(fan.channel_data.keys())}")

    info = printer.describe_printer_info()
    print(f"Printer info channels: {list(info.channel_data.keys())}")

    # Start background worker briefly
    printer.background_interval = 1.0
    printer.start()
    time.sleep(3)

    bed_temp = printer.get_channel("myPrinter.heater_bed.temperature", 1, True)
    ext_temp = printer.get_channel("myPrinter.extruder.temperature", 1, True)
    print(f"\nBackground worker results:")
    print(f"  Bed temp: {bed_temp.latest}")
    print(f"  Extruder temp: {ext_temp.latest}")

    print("\nSmoke test passed.")

finally:
    printer.close()
