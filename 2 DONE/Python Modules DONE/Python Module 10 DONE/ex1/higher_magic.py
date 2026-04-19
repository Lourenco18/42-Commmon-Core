from typing import Callable


def spell_combiner(spell1: Callable, spell2: Callable) -> Callable:
    def combined(*args, **kwargs):
        return (spell1(*args, **kwargs), spell2(*args, **kwargs))
    return combined


def power_amplifier(base_spell: Callable, multiplier: int) -> Callable:
    def amplified(*args, **kwargs):
        return base_spell(*args, **kwargs) * multiplier
    return amplified


def conditional_caster(condition: Callable, spell: Callable) -> Callable:
    def casted(*args, **kwargs):
        if condition(*args, **kwargs):
            return spell(*args, **kwargs)
        return "Spell fizzled"
    return casted


def spell_sequence(spells: list[Callable]) -> Callable:
    def sequence(*args, **kwargs):
        return [spell(*args, **kwargs) for spell in spells]
    return sequence


def main() -> None:
    def fireball(target: str) -> str:
        return f"Fireball hits {target}"

    def heal(target: str) -> str:
        return f"Heals {target}"

    def damage(target: str) -> int:
        return 10

    def is_enemy(target: str) -> bool:
        return target == "Dragon"

    print("Testing spell combiner...")
    combined = spell_combiner(fireball, heal)
    result = combined("Dragon")
    print(f"Combined spell result: {result[0]}, {result[1]}")

    print("\nTesting power amplifier...")
    mega_damage = power_amplifier(damage, 3)
    print(f"Original: {damage('Dragon')}, Amplified: {mega_damage('Dragon')}")

    print("\nTesting conditional caster...")
    conditional = conditional_caster(is_enemy, fireball)
    print(f"On Dragon: {conditional('Dragon')}")
    print(f"On Ally: {conditional('Ally')}")

    print("\nTesting spell sequence...")
    sequence = spell_sequence([fireball, heal])
    print(f"Sequence results: {sequence('Dragon')}")


if __name__ == "__main__":
    main()
