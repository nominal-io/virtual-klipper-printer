"""RTSP-to-Nominal video stream bridge.

Streams video from an RTSP source (e.g. MediaMTX) to a Nominal video
using the VideoStream SDK.

See: https://docs.nominal.io/core/sdk/python-client/video/live-video-streaming
"""

from __future__ import annotations

from nominal.core.video import Video
from nominal.experimental.video import ReconnectOptions, Src, StreamOptions, VideoStream

DEFAULT_STREAM_OPTIONS = StreamOptions(
    reconnect=ReconnectOptions(
        retry_delay_s=2.0,
        max_retries=None,
        disconnect_grace_s=5.0,
    ),
)


def stream_rtsp_to_nominal(
    video: Video,
    rtsp_url: str = "rtsp://localhost:8554/webcam",
    stream_options: StreamOptions | None = None,
    timeout: float | None = None,
) -> None:
    """Stream an RTSP source to a Nominal video. Blocks until interrupted.

    Uses TCP transport for RTSP to avoid UDP port forwarding issues with Docker.

    Args:
        video: A Nominal Video object (from ``client.create_video()`` or
            ``asset.get_or_create_video()``).
        rtsp_url: URL of the RTSP stream.
        stream_options: Optional StreamOptions for encoding control. If None,
            uses defaults with automatic reconnection.
        timeout: How long to stream in seconds. None = until Ctrl+C.
    """
    options = stream_options or DEFAULT_STREAM_OPTIONS

    # Use Src.custom() with rtspsrc protocols=tcp to force TCP transport,
    # avoiding UDP issues when MediaMTX runs inside Docker on macOS.
    src = Src.custom(f"rtspsrc location={rtsp_url} protocols=tcp latency=0 ! rtph264depay ! h264parse")

    with VideoStream.create(video, src, options) as stream:
        stream.run(timeout)
