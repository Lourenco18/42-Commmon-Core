from ex0.CreatureCard import CreatureCard
from ex1.SpellCard import SpellCard
from ex1.ArtifactCard import ArtifactCard
from ex1.Deck import Deck


def main():
    print("=== DataDeck Deck Builder ===")
    print("Building deck with different card types...")

    deck = Deck()
    deck.add_card(SpellCard(name="Lightning Bolt",
                            cost=3, rarity="Common", effect_type="damage"))
    deck.add_card(ArtifactCard(name="Mana Crystal",
                               cost=2, rarity="Rare", durability=5,
                               effect="+1 mana per turn"))
    deck.add_card(CreatureCard(name="Fire Dragon",
                               cost=5, rarity="Legendary", attack=7, health=5))

    print(f"Deck stats: {deck.get_deck_stats()}")

    print("\nDrawing and playing cards:")
    while True:
        try:
            card = deck.draw_card()
            card_type = card.get_card_info().get('type', 'Unknown')
            print(f"Drew: {card.name} ({card_type})")
            print(f"Play result: {card.play({})}")
        except IndexError:
            break

    print("\nPolymorphism in action: Same interface, "
          "different card behaviors!")


if __name__ == "__main__":
    main()
