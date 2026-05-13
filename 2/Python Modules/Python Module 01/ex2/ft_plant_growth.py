class Plant:
    def __init__(self, name: str, height: int, age: int) -> None:
        self.name = name
        self.height = height
        self.age = age

    def grow(self) -> None:
        self.height += 1

    def age_one_day(self) -> None:
        self.age += 1

    def print_plant_info(self) -> str:
        return f"{self.name}: {self.height}cm, {self.age} days old"


if __name__ == "__main__":
    rose = Plant("Rose", 25, 30)
    print("=== Day 1 ===")
    print(rose.print_plant_info())
    initial_height = rose.height
    for day in range(7):
        rose.grow()
        rose.age_one_day()

    print("=== Day 7 ===")
    print(rose.print_plant_info())

    growth_this_week = rose.height - initial_height
    print(f"Growth this week: +{growth_this_week}cm")
