from __future__ import annotations
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from zone import Zone
    from connection import Connection


class Drone:
    def __init__(self, drone_id: int, start_zone: "Zone") -> None:
        self.drone_id: int = drone_id
        self.current_zone: "Zone" = start_zone
        self.delivered: bool = False
        # Planned route as a list of zones (excluding the start zone)
        self.path: List["Zone"] = []
        # Index into path for next target
        self.path_index: int = 0
        # Turns remaining until the drone arrives at the next zone
        # (>1 means in transit over a restricted connection)
        self.turns_in_transit: int = 0
        # The connection currently being traversed (if in transit)
        self.transit_connection: Optional["Connection"] = None
        # The destination zone for the current transit
        self.transit_destination: Optional["Zone"] = None

    @property
    def label(self) -> str:
        return f"D{self.drone_id}"

    def next_target(self) -> Optional["Zone"]:
        if self.path_index < len(self.path):
            return self.path[self.path_index]
        return None

    def advance_path(self) -> None:
        self.path_index += 1

    def is_in_transit(self) -> bool:
        return self.turns_in_transit > 0

    def __repr__(self) -> str:
        return (
            f"Drone(id={self.drone_id}, "
            f"zone={self.current_zone.name!r}, "
            f"delivered={self.delivered})"
        )
