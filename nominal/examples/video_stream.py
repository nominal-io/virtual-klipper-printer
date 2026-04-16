"""Example: Stream printer webcam to Nominal via RTSP.

Connects to the MediaMTX RTSP stream and forwards video to Nominal.

Requires: GStreamer 1.20+, nominal[video]

Environment variables:
    NOMINAL_API_KEY       — Nominal API key (or uses stored credentials)
    NOMINAL_BASE_URL      — Nominal API base URL
    NOMINAL_WORKSPACE_RID — Workspace RID
    RTSP_URL              — RTSP stream URL (default: rtsp://localhost:8554/webcam)
    VIDEO_NAME            — Nominal video name (default: Virtual Klipper Webcam)

Usage:
    NOMINAL_API_KEY=your_key uv run python examples/video_stream.py
"""

import os

from nominal_moonraker import create_client, stream_rtsp_to_nominal

RTSP_URL = os.environ.get("RTSP_URL", "rtsp://localhost:8554/webcam")
VIDEO_NAME = os.environ.get("VIDEO_NAME", "Virtual Klipper Webcam")

client = create_client()
video = client.create_video(VIDEO_NAME)
print(f"Created Nominal video: {video.rid}")
print(f"Streaming {RTSP_URL} -> Nominal as '{VIDEO_NAME}'")
print("Press Ctrl+C to stop.")

try:
    stream_rtsp_to_nominal(video, RTSP_URL)
except KeyboardInterrupt:
    print("\nStopping...")
