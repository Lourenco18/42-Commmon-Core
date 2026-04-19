#!/usr/bin/env python3

def main() -> None:
    print("=== Game Analytics Dashboard ===")
    print()
    players = ['alice', 'bob', 'charlie', 'diana']
    scores = [2300, 1800, 2150, 2000]

    achievements = {
        'alice': ['first_kill', 'level_10', 'boss_slayer'],
        'bob': ['first_kill', 'explorer', 'strategist'],
        'charlie': ['first_kill', 'level_10', 'boss_slayer', 'collector',
                    'guardian', 'elite', 'veteran'],
        'diana': ['first_kill', 'level_10', 'boss_slayer', 'guardian']
    }

    player_regions = ['north', 'east', 'central', 'north']

    print("=== List Comprehension Examples ===")

    high_scorers = [players[i] for i in range(len(players))
                    if scores[i] > 2000]
    scores_doubled = [scores[i] * 2 for i in range(len(scores))]
    active_players = [players[i] for i in range(len(players))
                      if players[i] != 'diana']

    print("High scorers (>2000):", high_scorers)
    print("Scores doubled:", scores_doubled)
    print("Active players:", active_players)
    print()
    print("=== Dict Comprehension Examples ===")

    player_scores = {
        players[i]: scores[i]
        for i in range(len(players))
        if players[i] != 'diana'
    }

    score_categories = {
        'high': len([scores[i] for i in range(len(scores))
                     if scores[i] > 2000]),
        'medium': len([scores[i] for i in range(len(scores))
                       if 1800 <= scores[i] <= 2000]),
        'low': len([scores[i] for i in range(len(scores))
                    if scores[i] < 1800])
    }

    achievement_counts = {
        p: len(achievements[p])
        for p in achievements
        if p != 'diana'
    }

    print("Player scores:", player_scores)
    print("Score categories:", score_categories)
    print("Achievement counts:", achievement_counts)
    print()
    print("=== Set Comprehension Examples ===")

    unique_players = {players[i] for i in range(len(players))}

    unique_achievements = {
        achievements[p][i]
        for p in achievements
        for i in range(len(achievements[p]))
    }

    active_regions = {player_regions[i] for i in range(len(player_regions))}

    print("Unique players:", unique_players)
    print("Unique achievements:", unique_achievements)
    print("Active regions:", active_regions)
    print()
    print("=== Combined Analysis ===")

    total_players = len(players)

    total_unique_achievements = sum(
        [len(achievements[p]) for p in achievements]
    )

    average_score = sum(scores) / len(scores)

    highest_score = max(scores)

    for i in range(len(scores)):
        if scores[i] == highest_score:
            top_performer = players[i]

    print("Total players:", total_players)
    print("Total unique achievements:", total_unique_achievements)
    print("Average score:", average_score)
    print("Top performer:", top_performer,
          "("+str(highest_score)+" points,",
          str(len(achievements[top_performer]))+" achievements)")


if __name__ == "__main__":
    main()
