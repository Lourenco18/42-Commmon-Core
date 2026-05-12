from typing import Dict, List, Optional
from zone import Zone
from connection import Connection


class Graph:
    def __init__(self) -> None:
        """Initialize an empty Graph."""
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self.start: Optional[Zone] = None
        self.end: Optional[Zone] = None

    def add_zone(self, zone: Zone) -> None:
        if zone.name in self.zones:
            raise ValueError(f"Duplicate zone name: '{zone.name}'")
        self.zones[zone.name] = zone
        if zone.is_start:
            self.start = zone
        if zone.is_end:
            self.end = zone

    def add_connection(self, connection: Connection) -> None:
        for existing in self.connections:
            if (
                existing.connects(connection.zone_a)
                and existing.connects(connection.zone_b)
            ):
                raise ValueError(
                    f"Duplicate connection: '{connection.name}'"
                )
        self.connections.append(connection)

    def get_zone(self, name: str) -> Zone:
        if name not in self.zones:
            raise KeyError(f"Zone '{name}' not found in graph")
        return self.zones[name]

    def neighbors(self, zone: Zone) -> List[Zone]:
        result: List[Zone] = []
        for conn in self.connections:
            if conn.connects(zone):
                neighbor = conn.other(zone)
                result.append(neighbor)
        return result

    def get_connection(self, zone_a: Zone,
                       zone_b: Zone) -> Optional[Connection]:
        for conn in self.connections:
            if conn.connects(zone_a) and conn.connects(zone_b):
                return conn
        return None

    def validate_connectivity(self) -> None:
        """Raise ValueError if there is no path from start to end.

        Uses a simple BFS over accessible zones to check reachability.
        This is called after the full graph is built (by the Parser) so
        that all zones and connections are already present.
        """
        if self.start is None:
            raise ValueError("Graph has no start_hub zone")
        if self.end is None:
            raise ValueError("Graph has no end_hub zone")

        visited: set[str] = set()
        queue: List[Zone] = [self.start]
        visited.add(self.start.name)

        while queue:
            current = queue.pop(0)
            if current is self.end:
                return  # reachable
            for neighbor in self.neighbors(current):
                if neighbor.name not in visited and neighbor.is_accessible():
                    visited.add(neighbor.name)
                    queue.append(neighbor)

        raise ValueError(
            f"Graph is disconnected: no path exists from "
            f"'{self.start.name}' to '{self.end.name}'. "
            f"Check that every zone on the route has a connection and "
            f"that no required zone is 'blocked'."
        )

    def reset_capacities(self) -> None:
        for zone in self.zones.values():
            zone.current_drones = 0
        for conn in self.connections:
            conn.current_usage = 0

    def __repr__(self) -> str:
        return (
            f"Graph(zones={len(self.zones)}, "
            f"connections={len(self.connections)}, "
            f"start={self.start.name if self.start else None}, "
            f"end={self.end.name if self.end else None})"
        )