"""Stream telemetry and video from a Klipper printer to Nominal.

Runs the background telemetry worker and RTSP video stream in parallel.
Creates a Nominal asset with linked dataset and video for workbook viewing.

Environment variables:
    NOMINAL_API_KEY       — Nominal API key (or uses stored credentials)
    NOMINAL_BASE_URL      — Nominal API base URL (default: https://api.gov.nominal.io/api)
    NOMINAL_WORKSPACE_RID — Workspace RID to scope requests to
    ASSET_NAME            — Nominal asset name (default: Virtual Klipper Printer)
    RTSP_URL              — RTSP stream URL (default: rtsp://localhost:8554/webcam)
    MOONRAKER_HOST        — Moonraker host (default: localhost)
    MOONRAKER_PORT        — Moonraker port (default: 7125)

Usage:
    NOMINAL_API_KEY=key just stream
"""

import os
import threading
import time

from nominal_instro.lib.publishers import NominalCorePublisher
from nominal_moonraker import NominalMoonraker, create_client
from nominal_moonraker.video import stream_rtsp_to_nominal

RTSP_URL = os.environ.get("RTSP_URL", "rtsp://localhost:8554/webcam")
ASSET_NAME = os.environ.get("ASSET_NAME", "Virtual Klipper Printer")
MOONRAKER_HOST = os.environ.get("MOONRAKER_HOST", "localhost")
MOONRAKER_PORT = int(os.environ.get("MOONRAKER_PORT", "7125"))

# Nominal client
client = create_client()

# Create or find the asset
asset = client.create_asset(
    name=ASSET_NAME,
    description="Virtual Klipper 3D printer with telemetry and webcam",
    properties={"printer_type": "klipper", "host": MOONRAKER_HOST},
    labels=["klipper", "virtual-printer"],
)
print(f"Asset: {asset.rid}")

# Create dataset and video linked to the asset
dataset = asset.get_or_create_dataset(
    data_scope_name="telemetry",
    name=f"{ASSET_NAME} Telemetry",
    description="Printer telemetry: toolhead, extruder, heater bed, fan, print stats",
    prefix_tree_delimiter=".",
)
print(f"Dataset: {dataset.rid}")

video = asset.get_or_create_video(
    data_scope_name="webcam",
    name=f"{ASSET_NAME} Webcam",
    description="Live RTSP webcam feed via MediaMTX",
)
print(f"Video: {video.rid}")

# Telemetry
NOMINAL_API_KEY = os.environ.get("NOMINAL_API_KEY")
printer = NominalMoonraker(name="myPrinter", host=MOONRAKER_HOST, port=MOONRAKER_PORT)
publisher = NominalCorePublisher(dataset_rid=dataset.rid, api_key=NOMINAL_API_KEY)
printer.add_publisher(publisher)
printer.background_interval = 1.0

printer.open()
printer.set_event_context(client, asset.rid)

try:
    printer.start()

    # Run video streaming in a background thread (stream_rtsp_to_nominal blocks)
    video_thread = threading.Thread(
        target=stream_rtsp_to_nominal,
        args=(video, RTSP_URL),
        daemon=True,
    )
    video_thread.start()

    print(f"\nTelemetry  -> {dataset.rid}")
    print(f"Video      -> {video.rid}")
    print(f"Asset      -> {asset.rid}")
    print(f"Moonraker  : {MOONRAKER_HOST}:{MOONRAKER_PORT}")
    print(f"RTSP       : {RTSP_URL}")
    print("Press Ctrl+C to stop.\n")

    time.sleep(2)

    # Push channel units and hierarchy to Nominal now that channels exist
    printer.apply_channel_metadata(dataset)

    while True:
        try:
            bed = printer.get_channel("myPrinter.heater_bed.temperature", 1, True)
            ext = printer.get_channel("myPrinter.extruder.temperature", 1, True)
            print(f"Bed: {bed.latest}  Extruder: {ext.latest}")
        except KeyboardInterrupt:
            break

    print("\nShutting down...")

finally:
    printer.close()
