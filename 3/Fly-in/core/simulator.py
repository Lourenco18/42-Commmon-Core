from typing import Dict, List, Optional, Tuple
from graph import Graph
from zone import Zone
from connection import Connection
from drone import Drone
from pathfinder import Pathfinder


class SimulationResult:
    def __init__(self) -> None:
        self.turns: List[str] = []
        self.total_turns: int = 0


class Simulator:
    def __init__(self, graph: Graph, nb_drones: int) -> None:
        """Initialize the Simulator."""
        self.graph: Graph = graph
        self.nb_drones: int = nb_drones
        self.pathfinder: Pathfinder = Pathfinder(graph)
        self.drones: List[Drone] = []

    def run(self) -> SimulationResult:
        result = SimulationResult()

        if self.graph.start is None or self.graph.end is None:
            return result  # nothing to do

        # Build and assign paths
        self._initialize_drones()

        # Reset graph occupancy before simulation
        self.graph.reset_capacities()
        # Start zone hosts all drones initially (special exception)
        self.graph.start.current_drones = self.nb_drones

        max_turns = 10_000  # safety limit to prevent infinite loops
        for _ in range(max_turns):
            if all(d.delivered for d in self.drones):
                break

            turn_log = self._execute_turn()
            if turn_log:
                result.turns.append(turn_log)
                result.total_turns += 1
            else:
                # No movement happened — increment turn count anyway
                # to count waiting turns (but don't emit an empty line)
                result.total_turns += 1

        return result

    def _initialize_drones(self) -> None:
        """Create drones and assign each a planned path."""
        assert self.graph.start is not None
        assert self.graph.end is not None

        # Find multiple distinct paths
        paths = self.pathfinder.find_k_shortest_paths(
            self.graph.start, self.graph.end, k=self.nb_drones
        )
        if not paths:
            # No path exists — drones stay put
            for i in range(1, self.nb_drones + 1):
                d = Drone(i, self.graph.start)
                self.drones.append(d)
            return

        for i in range(1, self.nb_drones + 1):
            drone = Drone(i, self.graph.start)
            # Assign paths in round-robin so drones spread across routes
            chosen = paths[(i - 1) % len(paths)]
            # Path includes start zone; drone starts there, so skip index 0
            drone.path = chosen
            drone.path_index = 1
            self.drones.append(drone)

    def _execute_turn(self) -> str:
        movements: List[str] = []

        # Reset per-turn connection usage
        for conn in self.graph.connections:
            conn.current_usage = 0

        # Phase 1: determine intended moves for each drone
        intentions: List[Optional[Tuple[Drone, Zone, Connection]]] = []
        for drone in self.drones:
            if drone.delivered:
                intentions.append(None)
                continue
            intention = self._compute_intention(drone)
            intentions.append(intention)

        # Phase 2: resolve conflicts (capacity checks)
        # Count incoming drones per zone and per connection
        zone_incoming: Dict[str, int] = {}
        conn_incoming: Dict[str, int] = {}

        for intention in intentions:
            if intention is None:
                continue
            _, dest_zone, conn = intention
            zone_incoming[dest_zone.name] = (
                zone_incoming.get(dest_zone.name, 0) + 1
            )
            key = conn.name
            conn_incoming[key] = conn_incoming.get(key, 0) + 1

        # Phase 3: greedily approve moves (prioritise lower drone IDs)
        approved_zone: Dict[str, int] = {}
        approved_conn: Dict[str, int] = {}
        approved_moves: Dict[int, Tuple[Zone, Connection]] = {}

        for drone, intention in zip(self.drones, intentions):
            if intention is None:
                continue
            _, dest_zone, conn = intention
            z_name = dest_zone.name
            c_name = conn.name
            z_limit = dest_zone.max_drones if not dest_zone.is_end else 10 ** 9
            z_ok = approved_zone.get(z_name, 0) < z_limit
            c_ok = approved_conn.get(c_name, 0) < conn.max_link_capacity
            if z_ok and c_ok:
                approved_zone[z_name] = approved_zone.get(z_name, 0) + 1
                approved_conn[c_name] = approved_conn.get(c_name, 0) + 1
                approved_moves[drone.drone_id] = (dest_zone, conn)

        # Phase 4: apply approved moves, update state
        for drone in self.drones:
            if drone.delivered:
                continue
            move = approved_moves.get(drone.drone_id)
            if move is not None:
                dest_zone, conn = move
                drone.current_zone.current_drones -= 1
                dest_zone.current_drones += 1
                conn.current_usage += 1
                if dest_zone.zone_type == "restricted":
                    drone.turns_in_transit = 1
                    drone.transit_connection = conn
                    drone.transit_destination = dest_zone
                    drone.current_zone = dest_zone
                    drone.advance_path()
                    movements.append(f"{drone.label}-{conn.name}")
                else:
                    drone.current_zone = dest_zone
                    drone.advance_path()
                    movements.append(f"{drone.label}-{dest_zone.name}")
                if dest_zone is self.graph.end:
                    drone.delivered = True

        return " ".join(movements)

    def _compute_intention(
        self,
        drone: Drone,
    ) -> Optional[Tuple[Drone, Zone, "Connection"]]:
        # If drone is completing a restricted-zone transit
        if drone.is_in_transit():
            drone.turns_in_transit -= 1
            if drone.turns_in_transit == 0:
                drone.transit_destination = None
                drone.transit_connection = None
            return None  # already at destination from last turn

        next_zone = drone.next_target()
        if next_zone is None:
            return None  # no more path

        conn = self.graph.get_connection(drone.current_zone, next_zone)
        if conn is None:
            return None  # no connection (path invalid)

        if not next_zone.is_accessible():
            return None

        if not next_zone.has_capacity():
            return None

        if not conn.has_capacity():
            return None

        return (drone, next_zone, conn)
