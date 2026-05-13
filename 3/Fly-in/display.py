from typing import Dict, List
from graph import Graph
from simulator import SimulationResult

ANSI: Dict[str, str] = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "red":     "\033[91m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "blue":    "\033[94m",
    "magenta": "\033[95m",
    "cyan":    "\033[96m",
    "white":   "\033[97m",
    "gray":    "\033[90m",
    "orange":  "\033[33m",
}

ZONE_TYPE_COLORS: Dict[str, str] = {
    "normal":     "white",
    "restricted": "red",
    "priority":   "green",
    "blocked":    "gray",
}


class Display:
    def __init__(
        self,
        graph: Graph,
        nb_drones: int,
        use_color: bool = True,
    ) -> None:
        self.graph: Graph = graph
        self.nb_drones: int = nb_drones
        self.use_color: bool = use_color

    def print_header(self) -> None:
        sep = self._color("cyan", "=" * 60)
        print(sep)
        title = self._color("bold", "  FLY-IN  — Drone Routing Simulation")
        print(title)
        print(sep)
        start_name = self.graph.start.name if self.graph.start else "?"
        end_name = self.graph.end.name if self.graph.end else "?"
        print(
            f"  Drones : {self._color('yellow', str(self.nb_drones))}"
        )
        print(
            f"  Start  : {self._color('green', start_name)}"
        )
        print(
            f"  End    : {self._color('yellow', end_name)}"
        )
        print(
            f"  Zones  : {len(self.graph.zones)}"
        )
        print(
            f"  Links  : {len(self.graph.connections)}"
        )
        print(sep)
        self._print_zone_legend()
        print()

    def print_turn(self, turn_number: int, log_line: str) -> None:
        prefix = self._color("cyan", f"T{turn_number:>3} |")
        colored = self._colorize_log(log_line)
        print(f"{prefix} {colored}")

    def print_result(self, result: SimulationResult) -> None:
        sep = self._color("cyan", "=" * 60)
        print()
        print(sep)
        print(
            self._color("bold", "  SIMULATION COMPLETE")
        )
        print(sep)
        print(
            f"  Total turns    : "
            f"{self._color('yellow', str(result.total_turns))}"
        )
        print(
            f"  Drones routed  : "
            f"{self._color('green', str(self.nb_drones))}"
        )
        if result.total_turns > 0:
            avg = self.nb_drones / result.total_turns
            print(f"  Drones/turn    : {avg:.2f}")
        print(sep)

    def print_simulation_output(self, result: SimulationResult) -> None:
        print()
        print("=== Simulation Output ===")
        for line in result.turns:
            print(line)

    def _color(self, color_name: str, text: str) -> str:
        if not self.use_color:
            return text
        code = ANSI.get(color_name, "")
        if not code:
            return text
        return f"{code}{text}{ANSI['reset']}"

    def _colorize_log(self, log_line: str) -> str:
        tokens = log_line.split()
        colored_tokens: List[str] = []
        for token in tokens:
            if "-" in token:
                dash_idx = token.index("-")
                drone_part = token[:dash_idx]
                target_part = token[dash_idx + 1:]
                drone_colored = self._color("cyan", drone_part)
                zone_color = self._get_target_color(target_part)
                target_colored = self._color(zone_color, target_part)
                colored_tokens.append(f"{drone_colored}-{target_colored}")
            else:
                colored_tokens.append(token)
        return " ".join(colored_tokens)

    def _get_target_color(self, target_name: str) -> str:
        if "-" in target_name:
            return "orange"

        zone = self.graph.zones.get(target_name)
        if zone is None:
            return "white"

        if zone.color:
            color_name = zone.color.lower()
            if color_name in ANSI:
                return color_name

        type_color = ZONE_TYPE_COLORS.get(zone.zone_type, "white")
        return type_color

    def _print_zone_legend(self) -> None:
        print("  Zone types:")
        for ztype, color in ZONE_TYPE_COLORS.items():
            marker = self._color(color, f"  [{ztype}]")
            print(f"    {marker}")
