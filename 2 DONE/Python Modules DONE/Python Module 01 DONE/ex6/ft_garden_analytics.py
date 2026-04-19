
class Plant:
    def __init__(self, name: str, height: int = 0) -> None:
        self.name = name
        self.height = height
        self.plant_type = "regular"

    def grow(self) -> None:
        self.height += 1

    def get_info(self) -> str:
        return f"{self.name}: {self.height}cm"


class FloweringPlant(Plant):
    def __init__(self, name: str, height: int = 0,
                 color: str = "unknown") -> None:
        super().__init__(name, height)
        self.color = color
        self.is_blooming = False
        self.plant_type = "flowering"

    def bloom(self) -> None:
        self.is_blooming = True

    def _get_bloom_status(self) -> str:
        return "blooming" if self.is_blooming else "not blooming"

    def get_info(self) -> str:
        return (
            f"{self.name}: {self.height}cm, {self.color} flowers "
            f"({self._get_bloom_status()})"
        )


class PrizeFlower(FloweringPlant):
    def __init__(self, name: str, height: int = 0,
                 color: str = "unknown", prize_points: int = 0) -> None:
        super().__init__(name, height, color)
        self.prize_points = prize_points
        self.plant_type = "prize"

    def get_info(self) -> str:
        base_info = super().get_info()
        return f"{base_info}, Prize points: {self.prize_points}"


class Garden:
    def __init__(self, owner: str) -> None:
        self.owner = owner
        self.plants: list[Plant] = []
        self.stats = GardenManager.GardenStats()

    def add_plant(self, plant: Plant) -> None:
        self.plants.append(plant)
        self.stats.record_plant(plant)
        print(f"Added {plant.name} to {self.owner}'s garden")

    def help_plants_grow(self) -> None:
        print(f"{self.owner} is helping all plants grow...")
        for plant in self.plants:
            initial_height = plant.height
            plant.grow()
            growth = plant.height - initial_height
            self.stats.record_growth(growth)
            print(f"{plant.name} grew {growth}cm")

    def get_report(self) -> str:
        report = f"=== {self.owner}'s Garden Report ===\n"
        report += "Plants in garden:\n"
        for plant in self.plants:
            report += f"- {plant.get_info()}\n"
        report += f"\nPlants added: {self.stats.plants_added},"
        report += f"Total growth: {self.stats.total_growth}cm\n"
        report += ("Plant types: " +
                   f"{self.stats.plant_types_count['regular']} regular, " +
                   f"{self.stats.plant_types_count['flowering']} flowering, " +
                   f"{self.stats.plant_types_count['prize']} prize flowers")
        return report


class GardenManager:

    class GardenStats:
        def __init__(self) -> None:
            self.plants_added = 0
            self.total_growth = 0
            self.plant_types_count = {
                "regular": 0,
                "flowering": 0,
                "prize": 0
            }

        def record_growth(self, amount: int) -> None:
            self.total_growth += amount

        def record_plant(self, plant: Plant) -> None:
            self.plants_added += 1
            if plant.plant_type == "prize":
                self.plant_types_count["prize"] += 1
            elif plant.plant_type == "flowering":
                self.plant_types_count["flowering"] += 1
            else:
                self.plant_types_count["regular"] += 1

    gardens: dict[str, Garden] = {}

    @classmethod
    def create_garden(cls, owner: str) -> Garden:
        if owner not in cls.gardens:
            cls.gardens[owner] = Garden(owner)
        return cls.gardens[owner]

    @classmethod
    def create_garden_network(cls) -> None:
        cls.create_garden("Alice")
        cls.create_garden("Bob")

    @staticmethod
    def validate_height(height: int) -> bool:
        return height >= 0

    @classmethod
    def get_garden_scores(cls) -> dict[str, int]:
        scores = {}
        for owner in cls.gardens:
            garden = cls.gardens[owner]
            score = 0
            for plant in garden.plants:
                score += plant.height
            scores[owner] = score
        return scores


if __name__ == "__main__":

    print("=== Garden Management System Demo ===\n")

    GardenManager.create_garden_network()

    alice_garden = GardenManager.create_garden("Alice")
    bob_garden = GardenManager.create_garden("Bob")

    oak = Plant("Oak Tree", 140)  # corrigido para bater score Alice
    rose = FloweringPlant("Rose", 25, "red")
    rose.bloom()
    sunflower = PrizeFlower("Sunflower", 50, "yellow", 10)
    sunflower.bloom()

    alice_garden.add_plant(oak)
    alice_garden.add_plant(rose)
    alice_garden.add_plant(sunflower)
    print()
    alice_garden.help_plants_grow()
    print()
    print(alice_garden.get_report())
    print()
    bob_garden.add_plant(Plant("Cactus", 47))
    bob_garden.add_plant(Plant("Fern", 45))
    print()
    print("Height validation test:", GardenManager.validate_height(100))

    scores = GardenManager.get_garden_scores()
    print("Garden scores - Alice:", scores["Alice"], ", Bob:", scores["Bob"])

    count = 0
    for _ in GardenManager.gardens:
        count += 1
    print("Total gardens managed:", count)
