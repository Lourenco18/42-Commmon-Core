def ft_seed_inventory(seed: str, quantity: int, unit: str) -> None:
    name: str = seed.capitalize()
    if unit == "packets":
        print(f"{name} seeds: {quantity} packets available")
    elif unit == "grams":
        print(f"{name} seeds: {quantity} grams total")
    elif unit == "area":
        print(f"{name} seeds: covers {quantity} square meters")


ft_seed_inventory("tomato", 15, "packets")
