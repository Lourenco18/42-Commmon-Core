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
        self.graph: Graph = graph
        self.nb_drones: int = nb_drones
        self.pathfinder: Pathfinder = Pathfinder(graph)
        self.drones: List[Drone] = []

    def run(self) -> SimulationResult:
        result = SimulationResult()

        if self.graph.start is None or self.graph.end is None:
            return result

        self._initialize_drones()

        self.graph.reset_capacities()

        self.graph.start.current_drones = self.nb_drones

        max_turns = 10_000
        for _ in range(max_turns):
            if all(d.delivered for d in self.drones):
                break

            turn_log = self._execute_turn()
            if turn_log:
                result.turns.append(turn_log)
                result.total_turns += 1
            else:
                result.total_turns += 1

        return result

    def _initialize_drones(self) -> None:
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
            chosen = paths[(i - 1) % len(paths)]
            drone.path = chosen
            drone.path_index = 1
            self.drones.append(drone)

    def _execute_turn(self) -> str:
        movements: List[str] = []

        for conn in self.graph.connections:
            conn.current_usage = 0

        # Phase 1: collect candidate intentions (unconstrained — just next
        intentions: List[Optional[Tuple[Drone, Zone, Connection]]] = []
        for drone in self.drones:
            if drone.delivered:
                intentions.append(None)
                continue
            intention = self._compute_intention(drone)
            intentions.append(intention)

        # Phase 2: count how many drones are LEAVING each zone this turn
        zone_leaving: Dict[str, int] = {}
        for drone, intention in zip(self.drones, intentions):
            if intention is not None:
                name = drone.current_zone.name
                zone_leaving[name] = zone_leaving.get(name, 0) + 1

        # Phase 3: greedily approve moves (lower drone ID = higher priority).
        approved_zone_in: Dict[str, int] = {}
        approved_conn: Dict[str, int] = {}
        approved_moves: Dict[int, Tuple[Zone, Connection]] = {}

        for drone, intention in zip(self.drones, intentions):
            if intention is None:
                continue
            _, dest_zone, conn = intention
            z_name = dest_zone.name
            c_name = conn.name

            if dest_zone.is_end:
                z_limit = 10 ** 9
            else:
                leaving = zone_leaving.get(z_name, 0)
                z_limit = (
                    dest_zone.max_drones
                    - dest_zone.current_drones
                    + leaving
                )

            z_ok = approved_zone_in.get(z_name, 0) < z_limit
            c_ok = approved_conn.get(c_name, 0) < conn.max_link_capacity

            if z_ok and c_ok:
                approved_zone_in[z_name] = (
                    approved_zone_in.get(z_name, 0) + 1
                )
                approved_conn[c_name] = approved_conn.get(c_name, 0) + 1
                approved_moves[drone.drone_id] = (dest_zone, conn)

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
        if drone.is_in_transit():
            drone.turns_in_transit -= 1
            if drone.turns_in_transit == 0:
                drone.transit_destination = None
                drone.transit_connection = None
            return None

        next_zone = drone.next_target()
        if next_zone is None:
            return None

        conn = self.graph.get_connection(drone.current_zone, next_zone)
        if conn is None:
            return None

        if not next_zone.is_accessible():
            return None

        return (drone, next_zone, conn)
