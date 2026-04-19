class GardenError(Exception):
    pass


class InvalidPlantError(GardenError):
    pass


class WaterLevelError(GardenError):
    pass


class SunLevelError(GardenError):
    pass


class WaterTankError(GardenError):
    pass


class GardenManager:

    def __init__(self) -> None:
        self.plants: dict[str, dict[str, int]] = {}
        self.water_tank: int = 10

    def add_plant(self, name: str, water: int, sun: int) -> None:
        if not name or name.strip() == "":
            raise InvalidPlantError("Plant name cannot be empty!")

        if not isinstance(water, int) or not isinstance(sun, int):
            raise InvalidPlantError("Water and sun levels must be integers!")

        if water < 0 or sun < 0:
            raise InvalidPlantError("Water and sun levels must be positive!")

        self.plants[name] = {
            "water": water,
            "sun": sun
        }

    def water_plants(self) -> None:
        print("Opening watering system")

        try:
            if self.water_tank <= 0:
                raise WaterTankError("Not enough water in tank")

            for plant in self.plants:
                if self.water_tank <= 0:
                    raise WaterTankError("Not enough water in tank")

                self.plants[plant]["water"] += 1
                self.water_tank -= 1
                print(f"Watering {plant} - success")

        finally:
            print("Closing watering system (cleanup)")

    def check_plant_health(self, name: str) -> None:
        if name not in self.plants:
            raise InvalidPlantError("Plant does not exist!")

        water = self.plants[name]["water"]
        sun = self.plants[name]["sun"]

        if water > 10:
            raise WaterLevelError(f"Water level {water} is too high (max 10)")

        if sun > 10:
            raise SunLevelError(f"Sun level {sun} is too high (max 10)")

        print(f"{name}: healthy (water: {water}, sun: {sun})")


def test_garden_management() -> None:
    print("=== Garden Management System ===")

    manager = GardenManager()

    print("Adding plants to garden...")
    try:
        manager.add_plant("tomato", 4, 8)
        print("Added tomato successfully")

        manager.add_plant("lettuce", 5, 6)
        print("Added lettuce successfully")

        manager.add_plant("", 3, 5)
    except GardenError as e:
        print(f"Error adding plant: {e}")

    print("Watering plants...")
    try:
        manager.water_plants()
    except GardenError as e:
        print(f"Watering error: {e}")

    manager.plants["lettuce"]["water"] = 15

    print("Checking plant health...")
    for plant in manager.plants:
        try:
            manager.check_plant_health(plant)
        except GardenError as e:
            print(f"Error checking {plant}: {e}")

    print("Testing error recovery...")
    manager.water_tank = 0

    try:
        manager.water_plants()
    except GardenError as e:
        print(f"Caught GardenError: {e}")
        print("System recovered and continuing...")

    print("Garden management system test complete!")


if __name__ == "__main__":
    test_garden_management()
