from ex3.CardFactory import CardFactory
from ex3.GameStrategy import GameStrategy


class GameEngine:

    def __init__(self) -> None:
        self._factory: CardFactory | None = None
        self._strategy: GameStrategy | None = None
        self._turns_simulated: int = 0
        self._total_damage: int = 0
        self._cards_created: int = 0
        self._hand: list = []

    def configure_engine(self, factory: CardFactory,
                         strategy: GameStrategy) -> None:
        self._factory = factory
        self._strategy = strategy

        self._hand = [
            self._factory.create_creature('dragon'),
            self._factory.create_creature('goblin'),
            self._factory.create_spell(),
        ]
        self._cards_created = len(self._hand)

        print(f"Factory: {type(factory).__name__}")
        print(f"Strategy: {strategy.get_strategy_name()}")
        print(f"Available types: {factory.get_supported_types()}")

    def simulate_turn(self) -> dict:
        hand_summary = [f"{c.name} ({c.cost})" for c in self._hand]
        print(f"Hand: [{', '.join(hand_summary)}]")

        result = self._strategy.execute_turn(self._hand, [])
        self._turns_simulated += 1
        self._total_damage += result['actions']['damage_dealt']

        print("Turn execution:")
        print(f"Strategy: {result['strategy']}")
        print(f"Actions: {result['actions']}")
        return result

    def get_engine_status(self) -> dict:
        return {
            'turns_simulated': self._turns_simulated,
            'strategy_used': self._strategy.get_strategy_name()
            if self._strategy else None,
            'total_damage': self._total_damage,
            'cards_created': self._cards_created,
        }
