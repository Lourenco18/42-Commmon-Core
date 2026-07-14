#!/usr/bin/env python3

import sys


def main() -> None:
    args = sys.argv[1:]
    inventory = dict()

    for arg in args:
        if ':' in arg:
            name, qty = arg.split(':')
            inventory[name] = int(qty)

    total_items = sum(inventory.values())
    print("=== Inventory System Analysis ===")
    print(f"Total items in inventory: {total_items}")
    print(f"Unique item types: {len(inventory)}")
    print()
    print("=== Current Inventory ===")
    for item, qty in inventory.items():
        percent = (qty / total_items) * 100
        print(f"{item}: {qty} unit{'s' if qty > 1 else ''} ({percent:.1f}%)")

    most_abundant = max(inventory.items(), key=lambda x: x[1])
    least_abundant = min(inventory.items(), key=lambda x: x[1])
    print()
    print("=== Inventory Statistics ===")
    print(f"Most abundant: {most_abundant[0]} ({most_abundant[1]} units)")
    print(f"Least abundant: {least_abundant[0]} ({least_abundant[1]} units)")

    moderate = {k: v for k, v in inventory.items() if v > 3}
    scarce = {k: v for k, v in inventory.items() if v <= 3}
    print()
    print("=== Item Categories ===")
    print(f"Moderate: {moderate}")
    print(f"Scarce: {scarce}")
    print()
    restock = [k for k, v in inventory.items() if v <= 1]
    print("=== Management Suggestions ===")
    print(f"Restock needed: {restock}")
    print()
    print("=== Dictionary Properties Demo ===")
    print(f"Dictionary keys: {list(inventory.keys())}")
    print(f"Dictionary values: {list(inventory.values())}")
    print(f"Sample lookup - 'sword'in inventory: {'sword' in inventory}")


if __name__ == "__main__":
    main()
