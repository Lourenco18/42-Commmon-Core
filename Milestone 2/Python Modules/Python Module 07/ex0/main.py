from ex0.CreatureCard import CreatureCard


def main():
    print("=== DataDeck Card Foundation ===")
    print("Testing Abstract Base Class Design:")

    dragon = CreatureCard(name="Fire Dragon", cost=5, rarity="Legendary",
                          attack=7, health=5)

    print("\nCreatureCard Info:")
    print(dragon.get_card_info())

    available_mana = 6
    print(f"\nPlaying {dragon.name} with {available_mana} mana available:")
    print(f"Playable: {dragon.is_playable(available_mana)}")
    print(f"Play result: {dragon.play({})}")

    goblin = CreatureCard(name="Goblin Warrior", cost=1,
                          rarity="Common", attack=2, health=1)
    print(f"\n{dragon.name} attacks {goblin.name}:")
    print(f"Attack result: {dragon.attack_target(goblin)}")

    low_mana = 3
    print(f"\nTesting insufficient mana ({low_mana} available):")
    print(f"Playable: {dragon.is_playable(low_mana)}")

    print("\nAbstract pattern successfully demonstrated!")


if __name__ == "__main__":
    main()
