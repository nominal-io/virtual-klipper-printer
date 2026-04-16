"""Base types for Klipper printer object channel definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ChannelDef:
    """Metadata for a single channel within a Klipper printer object.

    Attributes:
        field_name: The Klipper field name (e.g. "temperature").
        description: Human-readable description of the channel.
        unit: UCUM unit string (e.g. "Cel", "mm", "mm/s", "1" for ratios).
            None for dimensionless counters or enums.
        value_type: Expected Python type from Klipper ("float", "int", "bool",
            "str", "list[float]"). Determines how values are serialized.
        labels: Static labels applied to this channel in Nominal.
        indexed: True if this is a positional array (e.g. [X,Y,Z,E]).
            Expanded to separate channels with [0], [1], etc. suffixes.
        index_names: Optional names for indexed positions (e.g. ["x","y","z","e"]).
    """

    field_name: str
    description: str = ""
    unit: str | None = None
    value_type: str = "float"
    labels: tuple[str, ...] = ()
    indexed: bool = False
    index_names: tuple[str, ...] = ()


@dataclass
class PrinterObject:
    """Base class defining a Klipper printer object's channel schema.

    Subclasses define `object_name` and `channels` to describe the fields
    available from a specific Klipper object.

    Attributes:
        object_name: The Klipper object name (e.g. "toolhead", "extruder").
        description: Human-readable description of the object.
        channels: Mapping of Klipper field names to ChannelDef metadata.
        labels: Labels applied to all channels in this object.
    """

    object_name: str
    description: str = ""
    channels: dict[str, ChannelDef] = field(default_factory=dict)
    labels: tuple[str, ...] = ()

    def get_channel(self, field_name: str) -> ChannelDef | None:
        return self.channels.get(field_name)

    def numeric_channels(self) -> dict[str, ChannelDef]:
        """Return only channels that produce numeric values."""
        return {
            k: v for k, v in self.channels.items()
            if v.value_type in ("float", "int", "bool", "list[float]")
        }
