"""Registry of all known Klipper printer objects.

Provides lookup functions and a default subscription set built from
the object definitions in ``definitions.py``.
"""

from __future__ import annotations

from nominal_moonraker.objects.base import PrinterObject
from nominal_moonraker.objects.definitions import (
    BED_MESH,
    DISPLAY_STATUS,
    EXTRUDER,
    FAN,
    FILAMENT_SWITCH_SENSOR,
    GCODE_MOVE,
    HEATER_BED,
    IDLE_TIMEOUT,
    MOTION_REPORT,
    OUTPUT_PIN,
    PRINT_STATS,
    TEMPERATURE_FAN,
    TEMPERATURE_SENSOR,
    TOOLHEAD,
    VIRTUAL_SDCARD,
    WEBHOOKS,
)

_ALL_OBJECTS: list[PrinterObject] = [
    TOOLHEAD,
    MOTION_REPORT,
    GCODE_MOVE,
    EXTRUDER,
    HEATER_BED,
    FAN,
    PRINT_STATS,
    VIRTUAL_SDCARD,
    DISPLAY_STATUS,
    IDLE_TIMEOUT,
    WEBHOOKS,
    TEMPERATURE_SENSOR,
    TEMPERATURE_FAN,
    BED_MESH,
    FILAMENT_SWITCH_SENSOR,
    OUTPUT_PIN,
]

REGISTRY: dict[str, PrinterObject] = {obj.object_name: obj for obj in _ALL_OBJECTS}

DEFAULT_SUBSCRIPTIONS: dict[str, list[str] | None] = {
    name: None for name in REGISTRY
}


def get_object(name: str) -> PrinterObject | None:
    """Look up a PrinterObject by its Klipper object name."""
    return REGISTRY.get(name)


def get_all_objects() -> dict[str, PrinterObject]:
    """Return a copy of the full registry."""
    return dict(REGISTRY)
