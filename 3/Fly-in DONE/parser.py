import re
from typing import Dict, Optional, Tuple
from graph import Graph
from zone import Zone
from connection import Connection


class ParseError(Exception):
    def __init__(self, line_number: int, message: str) -> None:
        """Initialize a ParseError."""
        super().__init__(f"Line {line_number}: {message}")
        self.line_number: int = line_number


class Parser:
    _META_RE = re.compile(r"\[([^\]]*)\]")
    _KV_RE = re.compile(r"(\w+)=(\S+)")

    def parse_file(self, filepath: str) -> Tuple[Graph, int]:
        with open(filepath, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        return self._parse_lines(lines)

    def parse_string(self, text: str) -> Tuple[Graph, int]:
        lines = text.splitlines(keepends=True)
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> Tuple[Graph, int]:
        graph = Graph()
        nb_drones: Optional[int] = None
        seen_connections: Dict[str, int] = {}
        start_count = 0
        end_count = 0

        for raw_lineno, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()

            # Skip blank lines and comments
            if not line or line.startswith("#"):
                continue

            # Strip inline comment
            comment_idx = line.find("#")
            if comment_idx != -1:
                line = line[:comment_idx].strip()
            if not line:
                continue

            if line.startswith("nb_drones:"):
                nb_drones = self._parse_nb_drones(line, raw_lineno)

            elif line.startswith("start_hub:"):
                if nb_drones is None:
                    raise ParseError(
                        raw_lineno,
                        "nb_drones must be defined before zone declarations"
                    )
                zone = self._parse_zone(line, "start_hub:", raw_lineno,
                                        is_start=True)
                start_count += 1
                if start_count > 1:
                    raise ParseError(raw_lineno,
                                     "Multiple start_hub zones defined")
                graph.add_zone(zone)

            elif line.startswith("end_hub:"):
                if nb_drones is None:
                    raise ParseError(
                        raw_lineno,
                        "nb_drones must be defined before zone declarations"
                    )
                zone = self._parse_zone(line, "end_hub:", raw_lineno,
                                        is_end=True)
                end_count += 1
                if end_count > 1:
                    raise ParseError(raw_lineno,
                                     "Multiple end_hub zones defined")
                graph.add_zone(zone)

            elif line.startswith("hub:"):
                if nb_drones is None:
                    raise ParseError(
                        raw_lineno,
                        "nb_drones must be defined before zone declarations"
                    )
                zone = self._parse_zone(line, "hub:", raw_lineno)
                graph.add_zone(zone)

            elif line.startswith("connection:"):
                self._parse_connection(
                    line, raw_lineno, graph, seen_connections
                )

            else:
                raise ParseError(raw_lineno, f"Unrecognized line: {line!r}")

        # Validate mandatory fields
        if nb_drones is None:
            raise ParseError(0, "Missing nb_drones declaration")
        if start_count == 0:
            raise ParseError(0, "Missing start_hub declaration")
        if end_count == 0:
            raise ParseError(0, "Missing end_hub declaration")

        return graph, nb_drones

    def _parse_nb_drones(self, line: str, lineno: int) -> int:
        parts = line.split(":", 1)
        if len(parts) != 2 or not parts[1].strip():
            raise ParseError(lineno, "Invalid nb_drones format")
        try:
            value = int(parts[1].strip())
        except ValueError:
            raise ParseError(lineno, "nb_drones must be an integer")
        if value < 1:
            raise ParseError(lineno, "nb_drones must be a positive integer")
        return value

    def _parse_zone(
        self,
        line: str,
        prefix: str,
        lineno: int,
        is_start: bool = False,
        is_end: bool = False,
    ) -> Zone:
        rest = line[len(prefix):].strip()

        # Extract optional metadata block
        meta: Dict[str, str] = {}
        meta_match = self._META_RE.search(rest)
        if meta_match:
            meta = self._parse_meta(meta_match.group(1), lineno)
            rest = rest[:meta_match.start()].strip()

        tokens = rest.split()
        if len(tokens) != 3:
            raise ParseError(
                lineno,
                f"Expected '<name> <x> <y>' after {prefix!r}, got {rest!r}"
            )
        name, x_str, y_str = tokens

        self._validate_zone_name(name, lineno)

        try:
            x = int(x_str)
            y = int(y_str)
        except ValueError:
            raise ParseError(
                lineno,
                f"Zone coordinates must be integers, got {x_str!r} {y_str!r}"
            )

        zone_type = meta.get("zone", "normal")
        if zone_type not in Zone.VALID_TYPES:
            raise ParseError(
                lineno,
                f"Invalid zone type '{zone_type}'. "
                f"Must be one of {Zone.VALID_TYPES}"
            )

        color = meta.get("color", None)

        max_drones_str = meta.get("max_drones", "1")
        try:
            max_drones = int(max_drones_str)
        except ValueError:
            raise ParseError(
                lineno,
                f"max_drones must be an integer, got {max_drones_str!r}"
            )
        if max_drones < 1:
            raise ParseError(
                lineno, "max_drones must be a positive integer"
            )

        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=is_start,
            is_end=is_end,
        )

    def _parse_connection(
        self,
        line: str,
        lineno: int,
        graph: Graph,
        seen: Dict[str, int],
    ) -> None:
        rest = line[len("connection:"):].strip()

        meta: Dict[str, str] = {}
        meta_match = self._META_RE.search(rest)
        if meta_match:
            meta = self._parse_meta(meta_match.group(1), lineno)
            rest = rest[:meta_match.start()].strip()

        parts = rest.split("-")
        if len(parts) != 2:
            raise ParseError(
                lineno,
                f"Connection must be '<zone1>-<zone2>', got {rest!r}"
            )
        name_a, name_b = parts[0].strip(), parts[1].strip()

        if not name_a or not name_b:
            raise ParseError(
                lineno, "Connection endpoints cannot be empty"
            )

        try:
            zone_a = graph.get_zone(name_a)
        except KeyError:
            raise ParseError(
                lineno, f"Unknown zone '{name_a}' in connection"
            )
        try:
            zone_b = graph.get_zone(name_b)
        except KeyError:
            raise ParseError(
                lineno, f"Unknown zone '{name_b}' in connection"
            )

        canonical = "-".join(sorted([name_a, name_b]))
        if canonical in seen:
            raise ParseError(
                lineno,
                f"Duplicate connection '{canonical}' "
                f"(first defined on line {seen[canonical]})"
            )
        seen[canonical] = lineno

        cap_str = meta.get("max_link_capacity", "1")
        try:
            capacity = int(cap_str)
        except ValueError:
            raise ParseError(
                lineno,
                f"max_link_capacity must be an integer, got {cap_str!r}"
            )
        if capacity < 1:
            raise ParseError(
                lineno, "max_link_capacity must be a positive integer"
            )

        connection = Connection(zone_a, zone_b, capacity)
        graph.add_connection(connection)

    def _parse_meta(self, meta_str: str, lineno: int) -> Dict[str, str]:
        result: Dict[str, str] = {}
        for match in self._KV_RE.finditer(meta_str):
            key, value = match.group(1), match.group(2)
            result[key] = value
        return result

    def _validate_zone_name(self, name: str, lineno: int) -> None:
        if "-" in name or " " in name:
            raise ParseError(
                lineno,
                f"Zone name '{name}' must not contain dashes or spaces"
            )
        if not name:
            raise ParseError(lineno, "Zone name cannot be empty")
