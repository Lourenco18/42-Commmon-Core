#!/usr/bin/env python3
import math


def distance(p1: tuple[int, int, int], p2: tuple[int, int, int]) -> float:

    x1, y1, z1 = p1
    x2, y2, z2 = p2
    return math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)


def parse_coordinates(coord_str: str) -> tuple[int, int, int] | None:
    try:
        parts = coord_str.split(',')
        x = int(parts[0])
        y = int(parts[1])
        z = int(parts[2])
        position = (x, y, z)
        print(f"Parsed position: {position}")
        dist = distance((0, 0, 0), position)
        print(f"Distance between (0, 0, 0) and {position}: {dist:.2f}")
        return position
    except Exception as e:
        print(f"Error parsing coordinates: {e}")
        print(f"Error details - Type: {type(e).__name__}, Args: {e.args}")
        return None


def main() -> None:
    print("=== Game Coordinate System ===\n")

    position = (10, 20, 5)
    print(f"Position created: {position}")
    print(
        f"Distance between (0, 0, 0) and {position}:"
        f"{distance((0, 0, 0), position):.2f}")

    coord_str = "3,4,0"
    print()
    print(f"Parsing coordinates: \"{coord_str}\"")
    parsed_position = parse_coordinates(coord_str)
    print()
    invalid_coord_str = "abc,def,ghi"
    print(f"Parsing invalid coordinates: \"{invalid_coord_str}\"")
    parse_coordinates(invalid_coord_str)
    print()
    if parsed_position:
        x, y, z = parsed_position
        print("Unpacking demonstration:")
        print(f"Player at x={x}, y={y}, z={z}")
        print(f"Coordinates: X={x}, Y={y}, Z={z}")


if __name__ == "__main__":
    main()
