class Plant:
    def __init__(self, name: str, height: int, age: int) -> None:
        self.name = name
        self.height = height
        self.age = age

    def print_plant_info(self) -> str:
        return f"{self.name} ({self.height}cm, {self.age} days)"


if __name__ == "__main__":
    count = 0
    print("=== Plant Factory Output ===")

    plants = [
        Plant("Rose", 25, 30),
        Plant("Oak", 200, 365),
        Plant("Cactus", 5, 90),
        Plant("Sunflower", 80, 45),
        Plant("Fern", 15, 120),
    ]

    for plant in plants:
        print(f"Created: {plant.print_plant_info()}")
        count += 1

    print(f"\nTotal plants created: {count}")
