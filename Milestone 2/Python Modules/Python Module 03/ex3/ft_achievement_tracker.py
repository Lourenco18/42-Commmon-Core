#!/usr/bin/env python3

def main() -> None:
    print("=== Achievement Tracker System ===")
    print()
    alice = set(['first_kill', 'level_10', 'treasure_hunter', 'speed_demon'])
    bob = set(['first_kill', 'level_10', 'boss_slayer', 'collector'])
    charlie = set(['level_10', 'treasure_hunter',
                   'boss_slayer', 'speed_demon', 'perfectionist'])
    print(f"Player alice achievements: {alice}")
    print(f"Player bob achievements: {bob}")
    print(f"Player charlie achievements: {charlie}")
    print()
    all_achievements = alice.union(bob).union(charlie)
    print("=== Achievement Analytics ===")
    print(f"All unique achievements: {all_achievements}")
    print(f"Total unique achievements: {len(all_achievements)}")
    print()
    common_all = alice.intersection(bob).intersection(charlie)
    print(f"Common to all players: {common_all}")

    rare_achievements = (alice.difference(bob.union(charlie))
                         .union(bob.difference(alice.union(charlie)))
                         .union(charlie.difference(alice.union(bob))))
    print(f"Rare achievements (1 player): {rare_achievements}")
    print()
    alice_bob_common = alice.intersection(bob)
    print(f"Alice vs Bob common: {alice_bob_common}")
    print(f"Alice unique: {alice.difference(bob)}")
    print(f"Bob unique: {bob.difference(alice)}")


if __name__ == "__main__":
    main()
