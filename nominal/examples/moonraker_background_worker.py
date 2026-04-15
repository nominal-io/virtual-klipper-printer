"""Example: Moonraker with background worker.

Demonstrates continuous data collection from a Klipper 3D printer via Moonraker,
with temperature control and live channel readout.

Optionally publishes to Nominal Core when a dataset RID is provided.
Set NOMINAL_API_KEY in the environment to authenticate (otherwise uses stored credentials).

Usage:
    # Local only (no publishing)
    uv run python examples/moonraker_background_worker.py

    # With Nominal Core publishing (uses stored credentials)
    uv run python examples/moonraker_background_worker.py <dataset_rid>

    # With Nominal Core publishing (uses env API key)
    NOMINAL_API_KEY=your_key uv run python examples/moonraker_background_worker.py <dataset_rid>

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
printer.background_interval = 1.0

printer.open()

try:
    printer.start()

    # Allow the daemon to gather some initial measurements.
    time.sleep(2)

    # Set bed and extruder temperatures.
    printer.set_temperature(60, heater="heater_bed")
    printer.set_temperature(200, heater="extruder")

    while True:
        try:
            bed_temp = printer.get_channel("myPrinter.heater_bed.temperature", 1, True)
            extruder_temp = printer.get_channel("myPrinter.extruder.temperature", 1, True)
            print(f"Bed: {bed_temp.latest}  Extruder: {extruder_temp.latest}")

        except KeyboardInterrupt:
            break

    print("Shutting down, setting temperatures to 0...")
    printer.set_temperature(0, heater="heater_bed")
    printer.set_temperature(0, heater="extruder")

finally:
    printer.close()
