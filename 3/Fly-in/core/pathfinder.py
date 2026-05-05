import heapq
from typing import Dict, List, Optional, Tuple
from graph import Graph
from zone import Zone


class Pathfinder:
    def __init__(self, graph: Graph) -> None:
        """Initialize the Pathfinder with a graph."""
        self.graph: Graph = graph

    def find_path(
        self,
        source: Zone,
        target: Zone,
    ) -> Optional[List[Zone]]:
        h_start = self._heuristic(source, target)
        heap: List[Tuple[float, float, str, List[Zone]]] = [
            (h_start, 0.0, source.name, [source])
        ]
        best_g: Dict[str, float] = {source.name: 0.0}

        while heap:
            f, g, current_name, path = heapq.heappop(heap)

            current_zone = self.graph.get_zone(current_name)

            if current_zone is target:
                return path

            if g > best_g.get(current_name, float("inf")):
                continue

            for neighbor in self.graph.neighbors(current_zone):
                if not neighbor.is_accessible():
                    continue

                step_cost = float(neighbor.movement_cost())
                new_g = g + step_cost

                if new_g < best_g.get(neighbor.name, float("inf")):
                    best_g[neighbor.name] = new_g
                    h = self._heuristic(neighbor, target)
                    new_f = new_g + h
                    heapq.heappush(
                        heap,
                        (new_f, new_g, neighbor.name, path + [neighbor])
                    )

        return None

    def find_k_shortest_paths(
        self,
        source: Zone,
        target: Zone,
        k: int = 5,
    ) -> List[List[Zone]]:
        first = self.find_path(source, target)
        if first is None:
            return []

        k_paths: List[List[Zone]] = [first]
        CandidateEntry = Tuple[float, int, List[Zone]]
        candidates: List[CandidateEntry] = []
        cand_counter: int = 0
        seen_paths: set[tuple[str, ...]] = {tuple(z.name for z in first)}

        for _ in range(k - 1):
            prev = k_paths[-1]

            for spur_idx in range(len(prev) - 1):
                spur_node = prev[spur_idx]
                root_path = prev[: spur_idx + 1]
                root_names = [z.name for z in root_path]

                removed_connections = self._block_used_connections(
                    k_paths, root_names
                )
                removed_nodes = set(root_names[:-1])

                spur_path = self._find_path_avoiding(
                    spur_node, target, removed_connections, removed_nodes
                )

                if spur_path is not None:
                    total = root_path[:-1] + spur_path
                    key = tuple(z.name for z in total)
                    if key not in seen_paths:
                        cost = self._path_cost(total)
                        heapq.heappush(candidates, (cost, cand_counter, total))
                        cand_counter += 1
                        seen_paths.add(key)

                _ = removed_connections

            if not candidates:
                break
            _, _ctr, best = heapq.heappop(candidates)
            k_paths.append(best)

        return k_paths

    def _heuristic(self, a: Zone, b: Zone) -> float:
        dx = float(a.x - b.x)
        dy = float(a.y - b.y)
        return float((dx * dx + dy * dy) ** 0.5)

    def _path_cost(self, path: List[Zone]) -> float:
        return sum(float(z.movement_cost()) for z in path[1:])

    def _block_used_connections(
        self,
        k_paths: List[List[Zone]],
        root_names: List[str],
    ) -> set[tuple[str, str]]:
        blocked: set[tuple[str, str]] = set()
        n = len(root_names)
        for path in k_paths:
            path_names = [z.name for z in path]
            if path_names[:n] == root_names and len(path_names) > n:
                a = root_names[-1]
                b = path_names[n]
                pair: tuple[str, str] = (
                    min(a, b), max(a, b)
                )
                blocked.add(pair)
        return blocked

    def _find_path_avoiding(
        self,
        source: Zone,
        target: Zone,
        blocked_connections: set[tuple[str, str]],
        blocked_nodes: set[str],
    ) -> Optional[List[Zone]]:
        h_start = self._heuristic(source, target)
        heap: List[Tuple[float, float, str, List[Zone]]] = [
            (h_start, 0.0, source.name, [source])
        ]
        best_g: Dict[str, float] = {source.name: 0.0}

        while heap:
            f, g, current_name, path = heapq.heappop(heap)
            current_zone = self.graph.get_zone(current_name)

            if current_zone is target:
                return path

            if g > best_g.get(current_name, float("inf")):
                continue

            for neighbor in self.graph.neighbors(current_zone):
                if not neighbor.is_accessible():
                    continue
                if neighbor.name in blocked_nodes:
                    continue
                pair = (
                    min(current_name, neighbor.name),
                    max(current_name, neighbor.name),
                )
                if pair in blocked_connections:
                    continue

                step_cost = float(neighbor.movement_cost())
                new_g = g + step_cost

                if new_g < best_g.get(neighbor.name, float("inf")):
                    best_g[neighbor.name] = new_g
                    h = self._heuristic(neighbor, target)
                    new_f = new_g + h
                    heapq.heappush(
                        heap,
                        (new_f, new_g, neighbor.name, path + [neighbor])
                    )

        return None
