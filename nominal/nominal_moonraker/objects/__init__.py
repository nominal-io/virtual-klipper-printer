"""Klipper printer object type definitions with channel metadata.

Each module defines a PrinterObject subclass that maps Klipper status fields
to typed channels with UCUM units, descriptions, and Nominal-compatible metadata.
"""

from nominal_moonraker.objects.base import ChannelDef, PrinterObject
from nominal_moonraker.objects.registry import REGISTRY, get_object, get_all_objects

__all__ = ["ChannelDef", "PrinterObject", "REGISTRY", "get_object", "get_all_objects"]
