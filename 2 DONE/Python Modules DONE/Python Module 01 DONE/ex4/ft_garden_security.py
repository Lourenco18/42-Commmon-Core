class SecurePlant:
    def __init__(self, name: str, height: int, age: int) -> None:
        self._name = name
        self._height = height
        self._age = age

    def set_height(self, height: int) -> bool:

        if height < 0:
            print("Security: Negative height rejected")
            return False
        self._height = height
        return True

    def set_age(self, age: int) -> bool:

        if age < 0:
            print("Security: Negative age rejected")
            return False
        self._age = age
        return True

    def get_height(self) -> int:

        return self._height

    def get_age(self) -> int:

        return self._age

    def get_name(self) -> str:

        return self._name

    def print_plant_info(self) -> str:

        return f"{self._name} ({self._height}cm, {self._age} days)"


if __name__ == "__main__":

    print("=== Garden Security System ===")

    plant = SecurePlant("Rose", 0, 0)
    print(f"Plant created: {plant.get_name()}")

    if plant.set_height(25):
        print(f"Height updated: {plant.get_height()}cm [OK]")

    if plant.set_age(30):
        print(f"Age updated: {plant.get_age()} days [OK]")

    print("\nInvalid operation attempted: height -5cm [REJECTED]")
    if not plant.set_height(-5):
        pass

    print(f"\nCurrent plant: {plant.print_plant_info()}")
