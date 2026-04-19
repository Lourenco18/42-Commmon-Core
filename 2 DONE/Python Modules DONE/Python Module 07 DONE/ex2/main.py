from ex2.EliteCard import EliteCard


def main():
    print("=== DataDeck Ability System ===")

    card_methods = ['play', 'get_card_info', 'is_playable']
    combatable_methods = ['attack', 'defend', 'get_combat_stats']
    magical_methods = ['cast_spell', 'channel_mana', 'get_magic_stats']

    print("EliteCard capabilities:")
    print(f"- Card: {card_methods}")
    print(f"- Combatable: {combatable_methods}")
    print(f"- Magical: {magical_methods}")

    warrior = EliteCard(
        name="Arcane Warrior",
        cost=6,
        rarity="Legendary",
        attack_power=5,
        defense=3,
        mana_pool=4,
    )

    print(f"\nPlaying {warrior.name} (Elite Card):")

    print("Combat phase:")
    print(f"Attack result: {warrior.attack('Enemy')}")
    print(f"Defense result: {warrior.defend(5)}")

    print("Magic phase:")
    print(f"Spell cast: {warrior.cast_spell('Fireball',
          ['Enemy1', 'Enemy2'])}")
    print(f"Mana channel: {warrior.channel_mana(3)}")

    print("\nMultiple interface implementation successful!")


if __name__ == "__main__":
    main()
