from typing import Optional


class Zone:
    VALID_TYPES = {"normal", "restricted", "priority", "blocked"}

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: str = "normal",
        color: Optional[str] = None,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Initialize a Zone."""
        if zone_type not in self.VALID_TYPES:
            raise ValueError(
                f"Invalid zone type '{zone_type}'. "
                f"Must be one of {self.VALID_TYPES}"
            )
        if max_drones < 1:
            raise ValueError(
                f"max_drones must be a positive integer, got {max_drones}"
            )
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: str = zone_type
        self.color: Optional[str] = color
        self.max_drones: int = max_drones
        self.is_start: bool = is_start
        self.is_end: bool = is_end
        # current occupancy (used during simulation)
        self.current_drones: int = 0

    def movement_cost(self) -> int:
        if self.zone_type == "restricted":
            return 2
        return 1

    def is_accessible(self) -> bool:
        return self.zone_type != "blocked"

    def has_capacity(self) -> bool:
        if self.is_end:
            return True
        return self.current_drones < self.max_drones

    def __repr__(self) -> str:
        """Return a string representation of the zone."""
        return (
            f"Zone(name={self.name!r}, type={self.zone_type!r}, "
            f"pos=({self.x},{self.y}), max_drones={self.max_drones})"
        )
