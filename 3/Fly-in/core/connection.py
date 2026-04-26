from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zone import Zone


class Connection:
    def __init__(
        self,
        zone_a: "Zone",
        zone_b: "Zone",
        max_link_capacity: int = 1,
    ) -> None:
        """Initialize a Connection."""
        if max_link_capacity < 1:
            raise ValueError(
                f"max_link_capacity must be a positive integer, "
                f"got {max_link_capacity}"
            )
        self.zone_a: "Zone" = zone_a
        self.zone_b: "Zone" = zone_b
        self.max_link_capacity: int = max_link_capacity
        self.current_usage: int = 0

    @property
    def name(self) -> str:
        names = sorted([self.zone_a.name, self.zone_b.name])
        return f"{names[0]}-{names[1]}"

    def other(self, zone: "Zone") -> "Zone":
        if zone is self.zone_a:
            return self.zone_b
        if zone is self.zone_b:
            return self.zone_a
        raise ValueError(
            f"Zone '{zone.name}' is not part of connection '{self.name}'"
        )

    def connects(self, zone: "Zone") -> bool:
        return zone is self.zone_a or zone is self.zone_b

    def has_capacity(self) -> bool:
        return self.current_usage < self.max_link_capacity

    def __repr__(self) -> str:
        return (
            f"Connection({self.zone_a.name!r} <-> {self.zone_b.name!r}, "
            f"cap={self.max_link_capacity})"
        )
