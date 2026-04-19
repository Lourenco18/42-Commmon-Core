#!/usr/bin/env python3

import sys


def main() -> None:
    print("=== Command Quest ===")

    total_args = len(sys.argv)

    if total_args == 1:
        print("No arguments provided!")
    print(f"Program name: {sys.argv[0]}")

    if total_args > 1:
        args_received = total_args - 1
        print(f"Arguments received: {args_received}")
        for i, arg in enumerate(sys.argv[1:], start=1):
            print(f"Argument {i}: {arg}")
    print(f"Total arguments: {total_args}")


if __name__ == "__main__":
    main()
