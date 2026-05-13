def water_plants(plant_list: list[str | None]) -> None:
    try:
        print("Opening watering system")
        for plant in plant_list:
            if not plant or plant.strip() == "":
                raise ValueError(
                    f"Cannot water {plant} - invalid plant!"
                )
            print(f"Watering {plant}")
    except ValueError as e:
        print(f"Error: {e}")
    finally:
        print("Closing watering system (cleanup)")


def test_watering_system() -> None:
    print("=== Garden Watering System ===")

    print("Testing normal watering...")
    good_plants = ["tomato", "lettuce", "carrots"]
    water_plants(good_plants)
    print("Watering completed successfully!\n")

    print("Testing with error...")
    bad_plants = ["tomato", None, "lettuce"]
    water_plants(bad_plants)
    print()
    print("Cleanup always happens, even with errors!")


if __name__ == "__main__":
    test_watering_system()
