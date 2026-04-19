def garden_operations() -> None:
    print("Testing ValueError...")
    try:
        int("abc")
    except ValueError as e:
        print(f"Caught ValueError: {e}")

    print("Testing ZeroDivisionError...")
    try:
        10 / 0
    except ZeroDivisionError as e:
        print(f"Caught ZeroDivisionError: {e}")

    print("Testing FileNotFoundError...")
    try:
        file = open("missing.txt", "r")
        file.close()
    except FileNotFoundError as e:
        print(f"Caught FileNotFoundError: {e}")

    print("Testing KeyError...")
    try:
        garden = {"flower": "rose"}
        print(garden["missing_plant"])
    except KeyError as e:
        print(f"Caught KeyError: {e}")


def test_error_types() -> None:
    print("=== Garden Error Types Demo ===\n")

    garden_operations()

    print("Testing multiple errors together...")
    try:
        int("xyz")
    except (ValueError, ZeroDivisionError):
        print("Caught an error, but program continues!")

    print("All error types tested successfully!")


if __name__ == "__main__":
    test_error_types()
