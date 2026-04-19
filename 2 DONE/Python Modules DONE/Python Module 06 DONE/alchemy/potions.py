from .elements import (
    create_fire,
    create_water,
    create_earth,
    create_air
)


def healing_potion() -> str:
    fire = create_fire()
    water = create_water()
    return f"Healing potion brewed with {fire} and {water}"


def strength_potion() -> str:
    earth = create_earth()
    fire = create_fire()
    return f"Strength potion brewed with {earth} and {fire}"


def invisibility_potion() -> str:
    air = create_air()
    water = create_water()
    return f"Invisibility potion brewed with {air} and {water}"


def wisdom_potion() -> str:
    fire = create_fire()
    water = create_water()
    earth = create_earth()
    air = create_air()
    return (
        f"Wisdom potion brewed with all elements: "
        f"{fire}, {water}, {earth}, {air}"
    )
