class GardenError(Exception):
    """A basic error for garden problems"""
    pass


class PlantError(GardenError):
    """For problems with plants"""
    pass


class WaterError(GardenError):
    """For problems with watering"""
    pass


def check_plant() -> None:
    raise PlantError("The tomato plant is wilting!")


def check_water() -> None:
    raise WaterError("Not enough water in the tank!")


def test_custom_errors() -> None:
    print("=== Custom Garden Errors Demo ===")

    print("Testing PlantError...")
    try:
        check_plant()
    except PlantError as e:
        print("Caught PlantError:", e)

    print("\nTesting WaterError...")
    try:
        check_water()
    except WaterError as e:
        print("Caught WaterError:", e)

    print("\nTesting catching all garden errors...")
    try:
        check_plant()
    except GardenError as e:
        print("Caught a garden error:", e)

    try:
        check_water()
    except GardenError as e:
        print("Caught a garden error:", e)

    print("\nAll custom error types work correctly!")


if __name__ == "__main__":
    test_custom_errors()
