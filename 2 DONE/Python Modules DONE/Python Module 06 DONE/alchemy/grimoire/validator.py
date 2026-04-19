def validate_ingredients(ingredients: str) -> str:
    valid_elements = ["fire", "water", "earth", "air"]

    if any(element in ingredients.lower() for element in valid_elements):
        return f"{ingredients} - VALID"

    return f"{ingredients} - INVALID"
