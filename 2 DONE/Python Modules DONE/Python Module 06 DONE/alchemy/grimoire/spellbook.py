def record_spell(spell_name: str, ingredients: str) -> str:
    from .validator import validate_ingredients

    validation = validate_ingredients(ingredients)

    if "VALID" in validation:
        return f"Spell recorded: {spell_name} ({validation})"

    return f"Spell rejected: {spell_name} ({validation})"
