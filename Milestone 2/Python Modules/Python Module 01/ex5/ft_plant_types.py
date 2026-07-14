class Plant:
    def __init__(self, name: str, height: int, age: int) -> None:
        self.name = name
        self.height = height
        self.age = age

    def print_plant_info(self) -> str:

        return f"{self.name}: {self.height}cm, {self.age} days"


class Flower(Plant):
    def __init__(self, name: str, height: int, age: int, color: str) -> None:
        super().__init__(name, height, age)
        self.color = color

    def bloom(self) -> None:
        print(f"{self.name} is blooming beautifully!\n")

    def print_flower_info(self) -> str:

        return f"{self.name} (Flower): {self.height}cm, {self.age} days, " \
               f"{self.color} color"


class Tree(Plant):

    def __init__(
        self,
        name: str,
        height: int,
        age: int,
        trunk_diameter: float
    ) -> None:
        super().__init__(name, height, age)
        self.trunk_diameter = trunk_diameter

    def produceShade(self) -> float:
        shade_area = (self.trunk_diameter / 100) * self.height / 10
        return shade_area

    def print_tree_info(self) -> str:
        return f"{self.name} (Tree): {self.height}cm, {self.age} days, " \
               f"{self.trunk_diameter}cm diameter"


class Vegetable(Plant):
    def __init__(
        self,
        name: str,
        height: int,
        age: int,
        harvest_season: str,
        nutritional_value: str
    ) -> None:
        super().__init__(name, height, age)
        self.harvest_season = harvest_season
        self.nutritional_value = nutritional_value

    def print_vegetable_info(self) -> str:
        return f"{self.name} (Vegetable): {self.height}cm, {self.age} days, " \
               f"{self.harvest_season} harvest"


if __name__ == "__main__":
    print("=== Garden Plant Types ===\n")
    rose = Flower("Rose", 25, 30, "red")
    oak = Tree("Oak", 500, 1825, 50)
    tomato = Vegetable("Tomato", 80, 90, "summer", "vitamin C")
    print(rose.print_plant_info())
    rose.bloom()

    print(oak.print_plant_info())
    shade = oak.produceShade()
    print(f"{oak.name} provides {shade:.0f} square meters of shade")
    print("")

    print(tomato.print_plant_info())
    print(f"{tomato.name} is rich in {tomato.nutritional_value}")
