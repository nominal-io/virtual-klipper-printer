"""Klipper printer object definitions with typed channel metadata.

Field specifications sourced from:
- https://moonraker.readthedocs.io/en/latest/printer_objects/
- Klipper v0.12.0-430

UCUM unit reference: https://ucum.org/ucum
"""

from nominal_moonraker.objects.base import ChannelDef, PrinterObject

# -- Position coordinate index names (Klipper convention: [X, Y, Z, E]) --
_XYZE = ("x", "y", "z", "e")
_XY = ("x", "y")


TOOLHEAD = PrinterObject(
    object_name="toolhead",
    description="Printer toolhead motion control and status",
    labels=("motion",),
    channels={
        "position": ChannelDef("position", "Commanded toolhead position", "mm", "list[float]", indexed=True, index_names=_XYZE),
        "axis_minimum": ChannelDef("axis_minimum", "Minimum valid move location", "mm", "list[float]", indexed=True, index_names=_XYZE),
        "axis_maximum": ChannelDef("axis_maximum", "Maximum valid move location", "mm", "list[float]", indexed=True, index_names=_XYZE),
        "print_time": ChannelDef("print_time", "Internal scheduling print time", "s", "float"),
        "estimated_print_time": ChannelDef("estimated_print_time", "Internal scheduling estimated print time", "s", "float"),
        "stalls": ChannelDef("stalls", "Times printer paused due to empty G-code buffer", None, "int"),
        "max_velocity": ChannelDef("max_velocity", "Current maximum velocity limit", "mm/s", "float"),
        "max_accel": ChannelDef("max_accel", "Current maximum acceleration limit", "mm.s-2", "float"),
        "minimum_cruise_ratio": ChannelDef("minimum_cruise_ratio", "Minimum portion of move at cruising speed", "1", "float"),
        "square_corner_velocity": ChannelDef("square_corner_velocity", "Maximum velocity for 90-degree corners", "mm/s", "float"),
    },
)

MOTION_REPORT = PrinterObject(
    object_name="motion_report",
    description="Real-time motion data from the toolhead",
    labels=("motion",),
    channels={
        "live_position": ChannelDef("live_position", "Estimated real-world toolhead position", "mm", "list[float]", indexed=True, index_names=_XYZE),
        "live_velocity": ChannelDef("live_velocity", "Estimated real-world toolhead velocity", "mm/s", "float"),
        "live_extruder_velocity": ChannelDef("live_extruder_velocity", "Estimated real-world active extruder velocity", "mm/s", "float"),
    },
)

GCODE_MOVE = PrinterObject(
    object_name="gcode_move",
    description="G-code movement state and position",
    labels=("motion", "gcode"),
    channels={
        "speed_factor": ChannelDef("speed_factor", "Feed rate percentage multiplier", "1", "float"),
        "speed": ChannelDef("speed", "Speed of most recent G-code move command", "mm/s", "float"),
        "extrude_factor": ChannelDef("extrude_factor", "Extrusion multiplier", "1", "float"),
        "absolute_coordinates": ChannelDef("absolute_coordinates", "True if in absolute coordinate mode", None, "bool"),
        "absolute_extrude": ChannelDef("absolute_extrude", "True if in absolute extrusion mode", None, "bool"),
        "homing_origin": ChannelDef("homing_origin", "G-code offset applied per axis", "mm", "list[float]", indexed=True, index_names=_XYZE),
        "position": ChannelDef("position", "Current position with offsets applied", "mm", "list[float]", indexed=True, index_names=_XYZE),
        "gcode_position": ChannelDef("gcode_position", "Current position without offsets", "mm", "list[float]", indexed=True, index_names=_XYZE),
    },
)

EXTRUDER = PrinterObject(
    object_name="extruder",
    description="Extruder heater and extrusion state",
    labels=("thermal", "extruder"),
    channels={
        "temperature": ChannelDef("temperature", "Current nozzle temperature", "Cel", "float"),
        "target": ChannelDef("target", "Requested nozzle temperature", "Cel", "float"),
        "power": ChannelDef("power", "PWM heater duty cycle (0.0-1.0)", "1", "float"),
        "can_extrude": ChannelDef("can_extrude", "Temperature above minimum extrusion threshold", None, "bool"),
        "pressure_advance": ChannelDef("pressure_advance", "Current pressure advance value", "s", "float"),
        "smooth_time": ChannelDef("smooth_time", "Velocity averaging window for pressure advance", "s", "float"),
    },
)

HEATER_BED = PrinterObject(
    object_name="heater_bed",
    description="Heated bed temperature control",
    labels=("thermal", "bed"),
    channels={
        "temperature": ChannelDef("temperature", "Current bed temperature", "Cel", "float"),
        "target": ChannelDef("target", "Target bed temperature", "Cel", "float"),
        "power": ChannelDef("power", "PWM heater duty cycle (0.0-1.0)", "1", "float"),
    },
)

FAN = PrinterObject(
    object_name="fan",
    description="Part cooling fan",
    labels=("cooling",),
    channels={
        "speed": ChannelDef("speed", "Fan speed percentage (0.0-1.0)", "1", "float"),
        "rpm": ChannelDef("rpm", "Fan revolutions per minute", "/min", "int"),
    },
)

PRINT_STATS = PrinterObject(
    object_name="print_stats",
    description="Current print job statistics",
    labels=("print",),
    channels={
        "total_duration": ChannelDef("total_duration", "Total job duration including pauses", "s", "float"),
        "print_duration": ChannelDef("print_duration", "Active printing time (excludes pauses)", "s", "float"),
        "filament_used": ChannelDef("filament_used", "Filament consumed during print", "mm", "float"),
    },
)

VIRTUAL_SDCARD = PrinterObject(
    object_name="virtual_sdcard",
    description="Virtual SD card file processing state",
    labels=("print",),
    channels={
        "progress": ChannelDef("progress", "Print file progress (0.0-1.0)", "1", "float"),
        "is_active": ChannelDef("is_active", "True when actively processing a file", None, "bool"),
        "file_position": ChannelDef("file_position", "Current byte position in file", "By", "int"),
        "file_size": ChannelDef("file_size", "Total file size", "By", "int"),
    },
)

DISPLAY_STATUS = PrinterObject(
    object_name="display_status",
    description="Display messages and print progress",
    labels=("print",),
    channels={
        "progress": ChannelDef("progress", "Print progress from M73 command (0.0-1.0)", "1", "float"),
    },
)

IDLE_TIMEOUT = PrinterObject(
    object_name="idle_timeout",
    description="Printer idle timeout state",
    labels=("system",),
    channels={
        "printing_time": ChannelDef("printing_time", "Time in Printing state since last reset", "s", "float"),
    },
)

WEBHOOKS = PrinterObject(
    object_name="webhooks",
    description="Klipper host software state",
    labels=("system",),
    channels={},  # state and state_message are strings — no numeric channels
)

TEMPERATURE_SENSOR = PrinterObject(
    object_name="temperature_sensor",
    description="Standalone temperature sensor",
    labels=("thermal", "sensor"),
    channels={
        "temperature": ChannelDef("temperature", "Current sensor temperature", "Cel", "float"),
        "measured_min_temp": ChannelDef("measured_min_temp", "Minimum reading since host start", "Cel", "float"),
        "measured_max_temp": ChannelDef("measured_max_temp", "Maximum reading since host start", "Cel", "float"),
    },
)

TEMPERATURE_FAN = PrinterObject(
    object_name="temperature_fan",
    description="Temperature-controlled fan",
    labels=("thermal", "cooling"),
    channels={
        "speed": ChannelDef("speed", "Fan speed percentage (0.0-1.0)", "1", "float"),
        "rpm": ChannelDef("rpm", "Fan RPM if tachometer configured", "/min", "int"),
        "temperature": ChannelDef("temperature", "Associated sensor temperature", "Cel", "float"),
        "target": ChannelDef("target", "Target activation temperature", "Cel", "float"),
    },
)

BED_MESH = PrinterObject(
    object_name="bed_mesh",
    description="Bed leveling mesh data",
    labels=("calibration",),
    channels={
        "mesh_min": ChannelDef("mesh_min", "Minimum mesh coordinate", "mm", "list[float]", indexed=True, index_names=_XY),
        "mesh_max": ChannelDef("mesh_max", "Maximum mesh coordinate", "mm", "list[float]", indexed=True, index_names=_XY),
    },
)

FILAMENT_SWITCH_SENSOR = PrinterObject(
    object_name="filament_switch_sensor",
    description="Filament presence sensor",
    labels=("sensor",),
    channels={
        "filament_detected": ChannelDef("filament_detected", "True when filament is detected", None, "bool"),
        "enabled": ChannelDef("enabled", "True when sensor is enabled", None, "bool"),
    },
)

OUTPUT_PIN = PrinterObject(
    object_name="output_pin",
    description="Output pin state",
    labels=("hardware",),
    channels={
        "value": ChannelDef("value", "Pin value (digital: 0/1, PWM: 0.0-1.0)", "1", "float"),
    },
)
