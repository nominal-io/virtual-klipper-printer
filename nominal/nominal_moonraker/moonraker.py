"""Moonraker 3D printer instrument interface.

Defines `NominalMoonraker` for communicating with Klipper-based 3D printers
via the Moonraker API.

Public API:
    NominalMoonraker

"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from nominal_moonraker.driver import MoonrakerDriver
from nominal_moonraker.objects.base import ChannelDef
from nominal_moonraker.objects.registry import DEFAULT_SUBSCRIPTIONS, get_all_objects, get_object
from nominal_instro.lib import Command, Measurement, NominalInstrument
from nominal_instro.lib.publishers.publisher import Publisher

if TYPE_CHECKING:
    from nominal.core import Dataset, NominalClient

logger = logging.getLogger(__name__)


class NominalMoonraker(NominalInstrument):
    """Moonraker 3D printer hardware abstraction.

    Uses the Moonraker websocket API to query printer state and send commands.
    Background telemetry is driven by Klipper subscriptions
    (``printer.objects.subscribe``) rather than polling — the printer pushes
    updates only when values change, reducing latency and network overhead.
    """

    def __init__(
        self,
        name: str,
        host: str,
        port: int = 7125,
        publishers: list[Publisher] | None = None,
        subscriptions: dict[str, list[str] | None] | None = None,
        **kwargs,
    ):
        """Initialize a NominalMoonraker instance.

        Args:
            name: Instrument name used in channel naming and published data.
            host: Hostname or IP of the Moonraker instance.
            port: Moonraker API port. Defaults to 7125.
            publishers: Publishers to send data to. Defaults to None.
            subscriptions: Klipper objects to subscribe to for background
                telemetry. Keys are object names, values are field lists
                (None = all fields). Defaults to ``DEFAULT_SUBSCRIPTIONS``.
            **kwargs: Tags applied to all Measurement/Command objects.
                Special: ``dataset_rid`` auto-creates a NominalCorePublisher.
        """
        super().__init__(name, connection_config=None, publishers=publishers, **kwargs)

        self._driver = MoonrakerDriver(host, port)
        self._resource_lock = threading.Lock()
        self._subscriptions = subscriptions if subscriptions is not None else DEFAULT_SUBSCRIPTIONS
        self._nominal_client: NominalClient | None = None
        self._asset_rid: str | None = None
        self._last_print_state: str | None = None

    def open(self):
        """Open a websocket connection to the Moonraker instance."""
        self._driver.open()

    def close(self):
        """Close the connection and clean up resources."""
        self._driver.close()
        super().close()

    def set_event_context(self, client: NominalClient, asset_rid: str) -> None:
        """Store the Nominal client and asset RID for creating events.

        Args:
            client: A ``NominalClient`` instance.
            asset_rid: The asset RID to attach events to.
        """
        self._nominal_client = client
        self._asset_rid = asset_rid

    # ── Background telemetry via subscriptions ──────────────────────────

    def start(self):
        """Start background telemetry collection via Klipper subscriptions.

        Sets up the channel buffer and background thread first, then subscribes
        to printer objects.  The initial subscription response (full state) is
        published immediately to seed the channel buffer so ``get_channel()``
        works right away.  Subsequent delta updates arrive asynchronously.
        """
        # Register a polling fallback so the background thread has something
        # to do even when subscriptions are quiet (idle printer).
        self.add_background_daemon_function(self._poll_subscribed_objects)

        # Set up channel buffer and background thread before subscribing,
        # so the buffer exists when the first notification arrives.
        super().start()

        self._driver.on_status_update(self._on_status_update)
        self._driver.on_gcode_response(self._on_gcode_response)

        # Subscribe and publish the initial full state to seed the buffer.
        with self._resource_lock:
            result = self._driver.subscribe_objects(self._subscriptions)
            timestamp = time.time_ns()

        status = result.get("status", {})
        for object_name, fields in status.items():
            if isinstance(fields, dict):
                self._to_measurement(object_name, fields, timestamp)

        # Seed the last known print state so the first delta doesn't
        # fire a spurious event.
        print_stats = status.get("print_stats", {})
        if isinstance(print_stats, dict) and "state" in print_stats:
            self._last_print_state = print_stats["state"]
            logger.info("Initial print state: %s", self._last_print_state)

    def _poll_subscribed_objects(self) -> None:
        """Polling fallback: query all subscribed objects once.

        Ensures fresh data reaches the channel buffer even when the printer
        is idle and subscriptions produce no delta updates.
        """
        with self._resource_lock:
            result = self._driver.query_objects(self._subscriptions)
            timestamp = time.time_ns()

        for object_name, fields in result.get("status", {}).items():
            if isinstance(fields, dict):
                self._to_measurement(object_name, fields, timestamp)

    def _on_status_update(self, status: dict, eventtime: float) -> None:
        """Handle a ``notify_status_update`` push from Klipper.

        Converts the delta dict into a Measurement and publishes it.
        """
        timestamp = time.time_ns()
        channel_data: dict[str, list[float]] = {}

        for object_name, fields in status.items():
            if not isinstance(fields, dict):
                continue
            self._flatten_fields(object_name, fields, channel_data)

        if channel_data:
            measurement = Measurement(
                channel_data=channel_data,
                timestamps=[timestamp],
                tags={**self.default_tags},
            )
            self.publish(measurement)

        # Check for print state changes and create events
        if "print_stats" in status:
            new_state = status["print_stats"].get("state")
            if new_state is not None and new_state != self._last_print_state:
                logger.info("Print state changed: %s -> %s", self._last_print_state, new_state)
                self._create_state_event(new_state, status["print_stats"])
                self._last_print_state = new_state

    # ── Describe: query any printer object ──────────────────────────────

    def describe(self, object_name: str, fields: list[str] | None = None, **kwargs) -> Measurement:
        """Query a Klipper printer object and return its status as a Measurement.

        Args:
            object_name: The Klipper object (e.g. "toolhead", "motion_report").
            fields: Specific fields to request. None = all fields.
            **kwargs: Tags for this measurement.

        Returns:
            Measurement containing the object's numeric fields.
        """
        with self._resource_lock:
            result = self._driver.query_objects({object_name: fields})
            timestamp = time.time_ns()

        status = result["status"][object_name]
        return self._to_measurement(object_name, status, timestamp, **kwargs)

    # ── Set: send G-code commands ───────────────────────────────────────

    def set_temperature(self, target: float, heater: str = "extruder", **kwargs) -> Command:
        """Set the target temperature for a heater.

        Args:
            target: Temperature in Celsius.
            heater: "extruder" or "heater_bed".
        """
        gcode = f"SET_HEATER_TEMPERATURE HEATER={heater} TARGET={target}"
        with self._resource_lock:
            self._driver.send_gcode(gcode)
            timestamp = time.time_ns()
        return self._to_command(f"set_temperature.{heater}", {"target": target}, timestamp, **kwargs)

    def set_fan_speed(self, speed: float, **kwargs) -> Command:
        """Set the part cooling fan speed (0.0 to 1.0)."""
        s_value = int(speed * 255)
        with self._resource_lock:
            self._driver.send_gcode(f"M106 S{s_value}")
            timestamp = time.time_ns()
        return self._to_command("set_fan_speed", {"speed": speed}, timestamp, **kwargs)

    def set_gcode(self, script: str, **kwargs) -> Command:
        """Send arbitrary G-code to the printer."""
        with self._resource_lock:
            self._driver.send_gcode(script)
            timestamp = time.time_ns()
        return self._to_command("gcode", {"script": script}, timestamp, **kwargs)

    # ── Create: start a print job ───────────────────────────────────────

    def create_print_job(self, filename: str, **kwargs) -> Command:
        """Start printing an uploaded G-code file."""
        with self._resource_lock:
            self._driver.start_print(filename)
            timestamp = time.time_ns()
        return self._to_command("create_print_job", {"filename": filename}, timestamp, **kwargs)

    # ── List: discover available objects ─────────────────────────────────

    def list_printer_objects(self) -> list[str]:
        """List all available Klipper printer objects."""
        with self._resource_lock:
            return self._driver.list_objects()

    # ── Emergency stop ───────────────────────────────────────────────────

    def emergency_stop(self, **kwargs) -> Command:
        """Trigger an emergency stop. Requires firmware restart afterwards."""
        with self._resource_lock:
            self._driver.emergency_stop()
            timestamp = time.time_ns()
        return self._to_command("emergency_stop", {}, timestamp, **kwargs)

    # ── Channel metadata ──────────────────────────────────────────────────

    def get_channel_metadata(self, object_name: str, field_name: str) -> ChannelDef | None:
        """Return the ``ChannelDef`` for a Klipper object field, or None if unknown.

        Args:
            object_name: The Klipper object name (e.g. "toolhead").
            field_name: The field within that object (e.g. "position").
        """
        printer_obj = get_object(object_name)
        if printer_obj is None:
            return None
        return printer_obj.get_channel(field_name)

    def apply_channel_metadata(self, dataset: Dataset) -> None:
        """Push channel units and hierarchy settings to a Nominal dataset.

        Iterates over every registered ``PrinterObject`` and its ``ChannelDef``
        entries, building a mapping of fully-qualified channel names to their
        UCUM unit strings.  Channels that don't yet exist in the dataset are
        silently skipped by the Nominal API.

        Args:
            dataset: A ``nominal.core.Dataset`` object (e.g. from
                ``asset.get_or_create_dataset()``).
        """
        channels_to_units: dict[str, str] = {}

        for object_name, printer_obj in get_all_objects().items():
            for field_name, channel_def in printer_obj.channels.items():
                if channel_def.unit is None:
                    continue

                channel_key = f"{self.name}.{object_name}.{field_name}"

                if channel_def.indexed and channel_def.index_names:
                    for index_name in channel_def.index_names:
                        channels_to_units[f"{channel_key}.{index_name}"] = channel_def.unit
                else:
                    channels_to_units[channel_key] = channel_def.unit

        dataset.set_channel_units(channels_to_units, allow_display_only_units=True)
        dataset.set_channel_prefix_tree(".")

    # ── Event and gcode helpers ──────────────────────────────────────────

    def _create_state_event(self, state: str, stats: dict) -> None:
        """Create a Nominal event for a print state change."""
        if self._nominal_client is None or self._asset_rid is None:
            return

        from nominal.core import EventType

        if state == "error":
            event_type = EventType.ERROR
        elif state == "cancelled":
            event_type = EventType.WARNING
        else:
            event_type = EventType.INFO

        properties: dict[str, str] = {}
        for key, value in stats.items():
            if isinstance(value, (str, int, float)):
                properties[key] = str(value)

        try:
            self._nominal_client.create_event(
                name=f"Print {state}",
                type=event_type,
                start=datetime.now(),
                duration=timedelta(seconds=0),
                assets=[self._asset_rid],
                properties=properties,
                labels=["klipper", "print_stats"],
            )
        except Exception:
            logger.exception("Failed to create state event for %r", state)

    def _on_gcode_response(self, message: str) -> None:
        """Handle a ``notify_gcode_response`` notification from Klipper."""
        command = Command(
            channel_data={f"{self.name}.gcode.response": message},
            timestamp=time.time_ns(),
            tags={**self.default_tags},
        )
        self.publish(command)

    # ── Internal helpers ─────────────────────────────────────────────────

    def _flatten_fields(
        self, object_name: str, fields: dict, channel_data: dict[str, list[float]]
    ) -> None:
        """Flatten a Klipper status dict into ``channel_data`` entries.

        Uses ``ChannelDef`` metadata from the registry when available.  For
        indexed channels with ``index_names``, the names are used as suffixes
        (e.g. ``myPrinter.toolhead.position.x``) instead of numeric indices.
        Falls back to ``[i]`` suffixes for unknown fields or channels without
        named indices.
        """
        printer_obj = get_object(object_name)

        for key, value in fields.items():
            channel_key = f"{self.name}.{object_name}.{key}"
            channel_def = printer_obj.get_channel(key) if printer_obj is not None else None

            if isinstance(value, bool):
                channel_data[channel_key] = [float(value)]
            elif isinstance(value, (int, float)):
                channel_data[channel_key] = [float(value)]
            elif isinstance(value, list) and value and all(isinstance(v, (int, float)) for v in value):
                if channel_def is not None and channel_def.indexed and channel_def.index_names:
                    for i, v in enumerate(value):
                        if i < len(channel_def.index_names):
                            suffix = channel_def.index_names[i]
                            channel_data[f"{channel_key}.{suffix}"] = [float(v)]
                        else:
                            channel_data[f"{channel_key}[{i}]"] = [float(v)]
                else:
                    for i, v in enumerate(value):
                        channel_data[f"{channel_key}[{i}]"] = [float(v)]

    def _to_measurement(self, object_name: str, status: dict, timestamp: int, **kwargs) -> Measurement:
        """Convert a Klipper object status dict into a Measurement."""
        channel_data: dict[str, list[float]] = {}
        self._flatten_fields(object_name, status, channel_data)

        measurement = Measurement(
            channel_data=channel_data,
            timestamps=[timestamp],
            tags={**self.default_tags, **(kwargs or {})},
        )
        self.publish(measurement)
        return measurement

    def _to_command(self, command_name: str, params: dict, timestamp: int, **kwargs) -> Command:
        """Convert command parameters into a Command object."""
        channel_data: dict[str, float | str] = {
            f"{self.name}.{command_name}.{key}.cmd": value
            for key, value in params.items()
        }

        command = Command(
            channel_data=channel_data,
            timestamp=timestamp,
            tags={**self.default_tags, **(kwargs or {})},
        )
        self.publish(command)
        return command
