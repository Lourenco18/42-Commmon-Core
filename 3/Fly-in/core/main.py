import sys
import argparse
from parser import Parser, ParseError
from simulator import Simulator
from display import Display


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="fly_in",
        description=(
            "Fly-in: route a fleet of drones from start to end "
            "in minimum simulation turns."
        ),
    )
    ap.add_argument(
        "map_file",
        help="Path to the drone network map file.",
    )
    ap.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable ANSI color output.",
    )
    ap.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable verbose debug output.",
    )
    return ap


def main() -> int:
    ap = build_arg_parser()
    args = ap.parse_args()

    parser = Parser()
    try:
        graph, nb_drones = parser.parse_file(args.map_file)
    except FileNotFoundError:
        print(f"Error: File not found: {args.map_file!r}", file=sys.stderr)
        return 1
    except ParseError as exc:
        print(f"Parse error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error during parsing: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 1

    use_color = not args.no_color
    display = Display(graph, nb_drones, use_color=use_color)
    display.print_header()

    # Run simulation
    simulator = Simulator(graph, nb_drones)
    try:
        result = simulator.run()
    except Exception as exc:
        print(f"Simulation error: {exc}", file=sys.stderr)
        if args.debug:
            raise
        return 1

    # Print turn-by-turn colored output
    for i, turn_line in enumerate(result.turns, start=1):
        display.print_turn(i, turn_line)

    # Print mandatory plain output format
    display.print_simulation_output(result)

    # Print statistics
    display.print_result(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
