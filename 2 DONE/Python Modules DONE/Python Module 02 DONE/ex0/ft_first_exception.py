def check_temperature(temp_str: str) -> int | None:
    try:
        temp = int(temp_str)
        if temp < 0:
            print(f"Error: {temp}°C is too cold for plants (min 0°C)\n")
            return None
        elif temp > 40:
            print(f"Error: {temp}°C is too hot for plants (max 40°C)\n")
            return None
        else:
            return temp

    except ValueError:
        print(f"Error: '{temp_str}' is not a valid number\n")
        return None


def test_temperature_input() -> None:
    print("=== Garden Temperature Checker ===")
    test_values = ["25", "abc", "100", "-50"]
    for value in test_values:
        print(f"Testing temperature: {value}")
        result = check_temperature(value)
        if result is not None:
            print(f"Temperature {result}°C is perfect for plants!\n")

    print("All tests completed - program didn't crash!")


if __name__ == "__main__":
    test_temperature_input()
