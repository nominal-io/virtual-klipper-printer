"""Moonraker 3D printer instrument interface.

Defines `NominalMoonraker` for communicating with Klipper-based 3D printers
via the Moonraker API.

Public API:
    NominalMoonraker

"""

import threading
import time
from typing import Any, Callable

from nominal_moonraker.driver import MoonrakerDriver
from nominal_instro.lib import Command, Measurement, NominalInstrument
from nominal_instro.lib.publishers.publisher import Publisher


class NominalMoonraker(NominalInstrument):
    """Moonraker 3D printer hardware abstraction to communicate with Klipper-based printers.

    Uses the Moonraker API via websocket to query printer state and send commands.
    Methods return Measurement and Command data types to be compatible with Nominal
    Instrumentation tools.
    """

    def __init__(
        self,
        name: str,
        host: str,
        port: int = 7125,
        publishers: list[Publisher] | None = None,
        **kwargs,
    ):
        """Initialize a NominalMoonraker instance.

        Args:
            name: A name to identify this instrument instance. Used in channel naming
                and published data.
            host: The hostname or IP address of the Moonraker instance.
            port: The port number for the Moonraker API. Defaults to 7125.
            publishers: List of publishers to send data to when executing methods.
                Defaults to None.
            **kwargs: Optional keyword arguments used as tags throughout the life of the
                instrument. These tags are applied to Measurement and Command objects and
                can be utilized by publishers like NominalCorePublisher as added metadata.

                Special keyword arguments:
                    dataset_rid (str): If provided, automatically creates and adds a
                        NominalCorePublisher with the specified dataset RID.
        """
        super().__init__(name, connection_config=None, publishers=publishers, **kwargs)

        self._driver = MoonrakerDriver(host, port)
        self._resource_lock = threading.Lock()

        self._define_background_daemon()

    def open(self):
        """Open a websocket connection to the Moonraker instance."""
        self._driver.open()

    def close(self):
        """Close the connection to the Moonraker instance and clean up resources."""
        self._driver.close()
        super().close()

    # ── Internal helpers ─────────────────────────────────────────────────

    def _execute_object_measurement(
        self, object_name: str, fields: list[str] | None = None, **kwargs
    ) -> Measurement:
        """Query a Klipper printer object and return its status as a Measurement.

        Args:
            object_name: The Klipper object to query (e.g. "toolhead", "extruder").
            fields: Optional list of fields to request. If None, all fields are returned.
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing the queried object's numeric fields.
        """
        with self._resource_lock:
            result = self._driver.query_objects({object_name: fields})
            timestamp = time.time_ns()

        status = result["status"][object_name]
        return self._to_measurement(object_name, status, timestamp, **kwargs)

    def _to_measurement(
        self, object_name: str, status: dict, timestamp: int, **kwargs
    ) -> Measurement:
        """Convert a Klipper object status dict into a Measurement.

        Numeric scalars and booleans are converted to float channels. Lists of all-numeric
        values are expanded into indexed channels. Strings, dicts, and None values are skipped.

        Args:
            object_name: The Klipper object name used in channel key construction.
            status: The status dict returned by Moonraker for the object.
            timestamp: Timestamp in nanoseconds.
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement with numeric channel data, published to all configured publishers.
        """
        channel_data: dict[str, list[float]] = {}

        for key, value in status.items():
            channel_key = f"{self.name}.{object_name}.{key}"

            if isinstance(value, (int, float)) and not isinstance(value, bool):
                channel_data[channel_key] = [float(value)]
            elif isinstance(value, bool):
                channel_data[channel_key] = [float(value)]
            elif isinstance(value, list) and value and all(isinstance(v, (int, float)) for v in value):
                for i, v in enumerate(value):
                    channel_data[f"{channel_key}[{i}]"] = [float(v)]

        measurement = Measurement(
            channel_data=channel_data,
            timestamps=[timestamp],
            tags={**self.default_tags, **(kwargs or {})},
        )
        self.publish(measurement)
        return measurement

    def _to_command(
        self, command_name: str, params: dict, timestamp: int, **kwargs
    ) -> Command:
        """Convert command parameters into a Command object.

        Args:
            command_name: Name of the command, used in channel key construction.
            params: Dict of parameter names to values.
            timestamp: Timestamp in nanoseconds.
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Command with channel data, published to all configured publishers.
        """
        channel_data: dict[str, float | str] = {}
        for key, value in params.items():
            channel_data[f"{self.name}.{command_name}.{key}.cmd"] = value

        command = Command(
            channel_data=channel_data,
            timestamp=timestamp,
            tags={**self.default_tags, **(kwargs or {})},
        )
        self.publish(command)
        return command

    # ── Describe verbs (return Measurement) ──────────────────────────────

    def describe_toolhead(self, **kwargs) -> Measurement:
        """Query the toolhead status including position, velocity, and homing state.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing toolhead status channels.
        """
        return self._execute_object_measurement("toolhead", **kwargs)

    def describe_extruder(self, **kwargs) -> Measurement:
        """Query the extruder status including temperature, target, and pressure advance.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing extruder status channels.
        """
        return self._execute_object_measurement("extruder", **kwargs)

    def describe_heater_bed(self, **kwargs) -> Measurement:
        """Query the heater bed status including temperature, target, and power.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing heater bed status channels.
        """
        return self._execute_object_measurement("heater_bed", **kwargs)

    def describe_print_stats(self, **kwargs) -> Measurement:
        """Query print job statistics including progress, print time, and filament used.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing print stats channels.
        """
        return self._execute_object_measurement("print_stats", **kwargs)

    def describe_fan(self, **kwargs) -> Measurement:
        """Query the part cooling fan status including speed and RPM.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing fan status channels.
        """
        return self._execute_object_measurement("fan", **kwargs)

    def describe_printer_info(self, **kwargs) -> Measurement:
        """Query general printer info via the printer.info endpoint.

        Uses the printer.info REST endpoint rather than objects.query.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Measurement containing printer info channels.
        """
        with self._resource_lock:
            result = self._driver.get_printer_info()
            timestamp = time.time_ns()
        return self._to_measurement("printer_info", result, timestamp, **kwargs)

    # ── Set verbs (return Command) ───────────────────────────────────────

    def set_temperature(self, target: float, heater: str = "extruder", **kwargs) -> Command:
        """Set the target temperature for a heater.

        Args:
            target: The target temperature in degrees Celsius.
            heater: The heater to control (e.g. "extruder", "heater_bed"). Defaults to "extruder".
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Command recording the temperature set point.
        """
        gcode = f"SET_HEATER_TEMPERATURE HEATER={heater} TARGET={target}"
        with self._resource_lock:
            self._driver.send_gcode(gcode)
            timestamp = time.time_ns()
        return self._to_command(f"set_temperature.{heater}", {"target": target}, timestamp, **kwargs)

    def set_fan_speed(self, speed: float, **kwargs) -> Command:
        """Set the part cooling fan speed.

        Args:
            speed: Fan speed as a float from 0.0 (off) to 1.0 (full speed).
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Command recording the fan speed setting.
        """
        s_value = int(speed * 255)
        gcode = f"M106 S{s_value}"
        with self._resource_lock:
            self._driver.send_gcode(gcode)
            timestamp = time.time_ns()
        return self._to_command("set_fan_speed", {"speed": speed}, timestamp, **kwargs)

    def set_gcode(self, script: str, **kwargs) -> Command:
        """Send an arbitrary G-code script to the printer.

        Args:
            script: The G-code script string to execute.
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Command recording the G-code that was sent.
        """
        with self._resource_lock:
            self._driver.send_gcode(script)
            timestamp = time.time_ns()
        return self._to_command("gcode", {"script": script}, timestamp, **kwargs)

    # ── Create verb ──────────────────────────────────────────────────────

    def create_print_job(self, filename: str, **kwargs) -> Command:
        """Start a print job from a file already uploaded to the printer.

        Args:
            filename: The filename of the G-code file to print.
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Command recording the print job creation.
        """
        with self._resource_lock:
            self._driver.start_print(filename)
            timestamp = time.time_ns()
        return self._to_command("create_print_job", {"filename": filename}, timestamp, **kwargs)

    # ── List verb ────────────────────────────────────────────────────────

    def list_printer_objects(self) -> list[str]:
        """List all available Klipper printer objects.

        Returns:
            List of printer object names that can be queried.
        """
        with self._resource_lock:
            return self._driver.list_objects()

    # ── Emergency stop ───────────────────────────────────────────────────

    def emergency_stop(self, **kwargs) -> Command:
        """Trigger an emergency stop on the printer.

        This immediately halts all printer motion and heaters. The printer will
        require a firmware restart after an emergency stop.

        Args:
            **kwargs: Optional keyword arguments used as tags.

        Returns:
            Command recording the emergency stop.
        """
        with self._resource_lock:
            self._driver.emergency_stop()
            timestamp = time.time_ns()
        return self._to_command("emergency_stop", {}, timestamp, **kwargs)

    # ── Background daemon ────────────────────────────────────────────────

    def _define_background_daemon(self):
        """Register default background daemon functions for continuous data collection.

        Registers toolhead, extruder, heater bed, print stats, and fan measurements
        to be periodically collected by the background worker thread.
        """
        self.add_background_daemon_function(self.describe_toolhead)
        self.add_background_daemon_function(self.describe_extruder)
        self.add_background_daemon_function(self.describe_heater_bed)
        self.add_background_daemon_function(self.describe_print_stats)
        self.add_background_daemon_function(self.describe_fan)
