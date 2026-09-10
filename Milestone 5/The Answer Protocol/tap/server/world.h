/* world.h - static + dynamic world state shared across the server.
 * "Static" data (room graph, NPC definitions, item definitions) is loaded
 * once from world.json. "Dynamic" data (which room an item instance is
 * currently in, NPC hp/alive, etc.) is mutated as players play.
 */
#ifndef TAP_WORLD_H
#define TAP_WORLD_H

#include <stddef.h>

#define MAX_ROOMS 64
#define MAX_EXITS 8
#define MAX_ITEMS 64
#define MAX_NPCS 32
#define MAX_DIALOGUE 8
#define ID_LEN 64
#define NAME_LEN 128
#define DESC_LEN 512

typedef struct {
    char direction[16];
    char target[ID_LEN];
} exit_t;

typedef struct {
    char id[ID_LEN];
    char name[NAME_LEN];
    char description[DESC_LEN];
    exit_t exits[MAX_EXITS];
    int exit_count;
} room_t;

/* An item *definition* (template). Only one instance of each item id
 * exists in the world at a time (per RFC 8: resource uniqueness). */
typedef struct {
    char id[ID_LEN];
    char name[NAME_LEN];
    char description[DESC_LEN];
    int obtainable;
    /* Dynamic location: room id if in a room, empty string if held by a
     * player (see player_t.inventory) or not yet spawned (reward items). */
    char room[ID_LEN];
} item_t;

typedef enum { ROLE_DIALOGUE, ROLE_QUEST_GIVER, ROLE_ENEMY } npc_role_t;

typedef struct {
    int active;              /* quest defined for this NPC? */
    char id[ID_LEN];
    char description[DESC_LEN];
    char require_item[ID_LEN];   /* fetch quest, empty if unused */
    char require_kill[ID_LEN];   /* defeat quest, empty if unused */
    int require_count;
    char reward_item[ID_LEN];
} quest_def_t;

typedef struct {
    char id[ID_LEN];
    char name[NAME_LEN];
    npc_role_t role;
    char room[ID_LEN];       /* home room (enemies/dialogue NPCs stay put) */
    char dialogue[MAX_DIALOGUE][DESC_LEN];
    int dialogue_count;
    int dialogue_next;       /* rotates through dialogue lines */
    quest_def_t quest;

    /* combat/dynamic state (only meaningful for role == ROLE_ENEMY) */
    int max_hp;
    int hp;
    int alive;
} npc_t;

typedef struct {
    char start_room[ID_LEN];
    room_t rooms[MAX_ROOMS];
    int room_count;
    item_t items[MAX_ITEMS];
    int item_count;
    npc_t npcs[MAX_NPCS];
    int npc_count;
} world_t;

/* Loads world.json (or the given path) into `w`. Returns 0 on success. */
int world_load(world_t *w, const char *path);

/* Lookup helpers. Return NULL if not found. */
room_t *world_find_room(world_t *w, const char *id);
item_t *world_find_item(world_t *w, const char *id_or_name);
npc_t *world_find_npc(world_t *w, const char *id_or_name);
item_t *world_find_item_in_room(world_t *w, const char *room_id, const char *id_or_name);
npc_t *world_find_npc_in_room(world_t *w, const char *room_id, const char *id_or_name);

/* Exposes the id/name resolution rule (see world.c) so callers such as the
 * server's inventory lookup can match "DROP Herbs" against item.herbs. */
int world_item_matches_query(const item_t *it, const char *query);

#endif
