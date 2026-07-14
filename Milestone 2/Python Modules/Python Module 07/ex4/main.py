from ex4.TournamentCard import TournamentCard
from ex4.TournamentPlatform import TournamentPlatform


def main():
    print("=== DataDeck Tournament Platform ===")
    print("Registering Tournament Cards...")

    dragon = TournamentCard(name="Fire Dragon", cost=5, rarity="Legendary",
                            attack_power=7, defense=5)
    wizard = TournamentCard(name="Ice Wizard",  cost=4, rarity="Rare",
                            attack_power=5, defense=4)

    platform = TournamentPlatform()
    dragon_id = platform.register_card(dragon)
    wizard_id = platform.register_card(wizard)

    for card_id, card in [(dragon_id, dragon), (wizard_id, wizard)]:
        print(f"{card.name} (ID: {card_id}):")
        print("- Interfaces: [Card, Combatable, Rankable]")
        print(f"- Rating: {card.rating}")
        print(f"- Record: {card.wins}-{card.losses}")

    print("\nCreating tournament match...")
    result = platform.create_match(dragon_id, wizard_id)
    print(f"Match result: {result}")

    print("\nTournament Leaderboard:")
    for entry in platform.get_leaderboard():
        card = platform._cards[entry['id']]
        print(f"{entry['rank']}. {entry['name']} - "
              f"Rating: {entry['rating']} ({entry['record']})")

    print("\nPlatform Report:")
    print(platform.generate_tournament_report())

    print("\n=== Tournament Platform Successfully Deployed! ===")
    print("All abstract patterns working together harmoniously!")


if __name__ == "__main__":
    main()
