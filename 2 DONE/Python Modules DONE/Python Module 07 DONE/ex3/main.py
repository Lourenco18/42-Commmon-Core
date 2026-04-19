from ex3.GameEngine import GameEngine
from ex3.FantasyCardFactory import FantasyCardFactory
from ex3.AggressiveStrategy import AggressiveStrategy


def main():
    print("=== DataDeck Game Engine ===")
    print("Configuring Fantasy Card Game...")

    engine = GameEngine()
    factory = FantasyCardFactory()
    strategy = AggressiveStrategy()

    engine.configure_engine(factory, strategy)

    print("\nSimulating aggressive turn...")
    engine.simulate_turn()

    print("\nGame Report:")
    print(engine.get_engine_status())

    print("\nAbstract Factory + Strategy Pattern: Maximum "
          "flexibility achieved!")


if __name__ == "__main__":
    main()
