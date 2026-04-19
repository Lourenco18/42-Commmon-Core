import random
from ex0.Card import Card
from ex0.CreatureCard import CreatureCard
from ex1.SpellCard import SpellCard
from ex1.ArtifactCard import ArtifactCard


class Deck:

    def __init__(self) -> None:
        self._cards: list[Card] = []

    def add_card(self, card: Card) -> None:
        self._cards.append(card)

    def remove_card(self, card_name: str) -> bool:
        for i, card in enumerate(self._cards):
            if card.name == card_name:
                self._cards.pop(i)
                return True
        return False

    def shuffle(self) -> None:
        random.shuffle(self._cards)

    def draw_card(self) -> Card:
        if not self._cards:
            raise IndexError("Cannot draw from an empty deck")
        return self._cards.pop(0)

    def get_deck_stats(self) -> dict:
        total = len(self._cards)
        creatures = sum(1 for c in self._cards if isinstance(c, CreatureCard))
        spells = sum(1 for c in self._cards if isinstance(c, SpellCard))
        artifacts = sum(1 for c in self._cards if isinstance(c, ArtifactCard))
        avg_cost = round(sum(c.cost for c in
                             self._cards) / total, 1) if total else 0.0
        return {
            'total_cards': total,
            'creatures': creatures,
            'spells': spells,
            'artifacts': artifacts,
            'avg_cost': avg_cost,
        }
