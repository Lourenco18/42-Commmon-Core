#include "world.h"
#include "../common/jsonmin.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

static char *read_whole_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *buf = malloc((size_t)sz + 1);
    size_t n = fread(buf, 1, (size_t)sz, f);
    buf[n] = '\0';
    fclose(f);
    return buf;
}

static void copy_str(char *dst, size_t cap, const json_value_t *v, const char *def) {
    const char *s = json_as_str(v);
    if (!s) s = def;
    snprintf(dst, cap, "%s", s);
}

int world_load(world_t *w, const char *path) {
    memset(w, 0, sizeof(*w));
    char *text = read_whole_file(path);
    if (!text) {
        fprintf(stderr, "error: cannot read world file '%s'\n", path);
        return -1;
    }
    json_value_t *root = json_parse(text);
    free(text);
    if (!root) {
        fprintf(stderr, "error: cannot parse world file '%s' (invalid JSON)\n", path);
        return -1;
    }

    json_value_t *start = json_obj_get(root, "start_room");
    copy_str(w->start_room, sizeof(w->start_room), start, "");

    /* --- rooms --- */
    json_value_t *rooms = json_obj_get(root, "rooms");
    if (rooms && rooms->type == JV_OBJ) {
        for (size_t i = 0; i < rooms->u.obj.count && w->room_count < MAX_ROOMS; i++) {
            room_t *r = &w->rooms[w->room_count];
            snprintf(r->id, sizeof(r->id), "%s", rooms->u.obj.keys[i]);
            json_value_t *rv = rooms->u.obj.vals[i];
            copy_str(r->name, sizeof(r->name), json_obj_get(rv, "name"), r->id);
            copy_str(r->description, sizeof(r->description), json_obj_get(rv, "description"), "");
            json_value_t *exits = json_obj_get(rv, "exits");
            if (exits && exits->type == JV_OBJ) {
                for (size_t e = 0; e < exits->u.obj.count && r->exit_count < MAX_EXITS; e++) {
                    snprintf(r->exits[r->exit_count].direction, sizeof(r->exits[0].direction), "%s", exits->u.obj.keys[e]);
                    copy_str(r->exits[r->exit_count].target, sizeof(r->exits[0].target), exits->u.obj.vals[e], "");
                    r->exit_count++;
                }
            }
            w->room_count++;
        }
    }

    /* --- items --- */
    json_value_t *items = json_obj_get(root, "items");
    if (items && items->type == JV_OBJ) {
        for (size_t i = 0; i < items->u.obj.count && w->item_count < MAX_ITEMS; i++) {
            item_t *it = &w->items[w->item_count];
            snprintf(it->id, sizeof(it->id), "%s", items->u.obj.keys[i]);
            json_value_t *iv = items->u.obj.vals[i];
            copy_str(it->name, sizeof(it->name), json_obj_get(iv, "name"), it->id);
            copy_str(it->description, sizeof(it->description), json_obj_get(iv, "description"), "");
            json_value_t *obtainable = json_obj_get(iv, "obtainable");
            it->obtainable = obtainable && obtainable->type == JV_BOOL ? obtainable->u.boolean : 0;
            json_value_t *room = json_obj_get(iv, "room");
            const char *room_s = json_as_str(room);
            if (room_s) snprintf(it->room, sizeof(it->room), "%s", room_s);
            else it->room[0] = '\0'; /* not yet spawned (e.g. quest reward) */
            w->item_count++;
        }
    }

    /* --- npcs --- */
    json_value_t *npcs = json_obj_get(root, "npcs");
    if (npcs && npcs->type == JV_OBJ) {
        for (size_t i = 0; i < npcs->u.obj.count && w->npc_count < MAX_NPCS; i++) {
            npc_t *n = &w->npcs[w->npc_count];
            snprintf(n->id, sizeof(n->id), "%s", npcs->u.obj.keys[i]);
            json_value_t *nv = npcs->u.obj.vals[i];
            copy_str(n->name, sizeof(n->name), json_obj_get(nv, "name"), n->id);
            copy_str(n->room, sizeof(n->room), json_obj_get(nv, "room"), "");
            const char *role_s = json_as_str(json_obj_get(nv, "role"));
            if (role_s && strcasecmp(role_s, "quest_giver") == 0) n->role = ROLE_QUEST_GIVER;
            else if (role_s && strcasecmp(role_s, "enemy") == 0) n->role = ROLE_ENEMY;
            else n->role = ROLE_DIALOGUE;

            json_value_t *dlg = json_obj_get(nv, "dialogue");
            n->dialogue_count = 0;
            if (dlg && dlg->type == JV_ARR) {
                for (size_t d = 0; d < json_arr_len(dlg) && n->dialogue_count < MAX_DIALOGUE; d++) {
                    const char *line = json_as_str(json_arr_get(dlg, d));
                    if (line) snprintf(n->dialogue[n->dialogue_count++], DESC_LEN, "%s", line);
                }
            }

            json_value_t *hp = json_obj_get(nv, "hp");
            n->max_hp = (int)json_as_num(hp, 20);
            n->hp = n->max_hp;
            n->alive = 1;

            json_value_t *q = json_obj_get(nv, "quest");
            memset(&n->quest, 0, sizeof(n->quest));
            if (q) {
                n->quest.active = 1;
                copy_str(n->quest.id, sizeof(n->quest.id), json_obj_get(q, "id"), "");
                copy_str(n->quest.description, sizeof(n->quest.description), json_obj_get(q, "description"), "");
                copy_str(n->quest.require_item, sizeof(n->quest.require_item), json_obj_get(q, "require_item"), "");
                copy_str(n->quest.require_kill, sizeof(n->quest.require_kill), json_obj_get(q, "require_kill"), "");
                copy_str(n->quest.reward_item, sizeof(n->quest.reward_item), json_obj_get(q, "reward_item"), "");
                n->quest.require_count = (int)json_as_num(json_obj_get(q, "require_count"), 1);
            }

            w->npc_count++;
        }
    }

    json_free(root);

    /* --- validation: every exit target and start room must exist --- */
    int ok = 1;
    if (!world_find_room(w, w->start_room)) {
        fprintf(stderr, "error: start_room '%s' does not exist\n", w->start_room);
        ok = 0;
    }
    for (int i = 0; i < w->room_count; i++) {
        for (int e = 0; e < w->rooms[i].exit_count; e++) {
            if (!world_find_room(w, w->rooms[i].exits[e].target)) {
                fprintf(stderr, "error: room '%s' exit '%s' points to unknown room '%s'\n",
                        w->rooms[i].id, w->rooms[i].exits[e].direction, w->rooms[i].exits[e].target);
                ok = 0;
            }
        }
    }
    for (int i = 0; i < w->item_count; i++) {
        if (w->items[i].room[0] && !world_find_room(w, w->items[i].room)) {
            fprintf(stderr, "error: item '%s' placed in unknown room '%s'\n", w->items[i].id, w->items[i].room);
            ok = 0;
        }
    }
    for (int i = 0; i < w->npc_count; i++) {
        if (w->npcs[i].room[0] && !world_find_room(w, w->npcs[i].room)) {
            fprintf(stderr, "error: npc '%s' placed in unknown room '%s'\n", w->npcs[i].id, w->npcs[i].room);
            ok = 0;
        }
        if (w->npcs[i].quest.active && w->npcs[i].quest.require_item[0] &&
            !world_find_item(w, w->npcs[i].quest.require_item)) {
            fprintf(stderr, "error: npc '%s' quest requires unknown item '%s'\n", w->npcs[i].id, w->npcs[i].quest.require_item);
            ok = 0;
        }
        if (w->npcs[i].quest.active && w->npcs[i].quest.reward_item[0] &&
            !world_find_item(w, w->npcs[i].quest.reward_item)) {
            fprintf(stderr, "error: npc '%s' quest rewards unknown item '%s'\n", w->npcs[i].id, w->npcs[i].quest.reward_item);
            ok = 0;
        }
    }
    return ok ? 0 : -1;
}

/* Case-insensitive substring search (portable strcasestr replacement). */
static int ci_contains(const char *haystack, const char *needle) {
    if (!haystack || !needle || !*needle) return 0;
    size_t hn = strlen(haystack), nn = strlen(needle);
    if (nn > hn) return 0;
    for (size_t i = 0; i + nn <= hn; i++)
        if (strncasecmp(haystack + i, needle, nn) == 0) return 1;
    return 0;
}

/* Returns the part of an id after the last '.', e.g. "npc.goblin" -> "goblin". */
static const char *local_part(const char *id) {
    const char *dot = strrchr(id, '.');
    return dot ? dot + 1 : id;
}

/* Resource resolution per RFC 8.3/8.4: a resource may be referenced by its
 * canonical id or its (possibly multi-word) display name. In practice, and
 * as shown by the RFC's own examples ("TAKE Herbs" resolving item.herbs
 * named "Healing Herbs"; "TALK Baker" resolving a "Baker" NPC), clients
 * also send short/partial names. We therefore match, in priority order:
 *   1. exact id match
 *   2. exact display-name match (case-insensitive)
 *   3. exact match against the id's local part (after the last '.')
 *   4. case-insensitive substring match against the display name or the
 *      id's local part
 * This is documented as a protocol clarification in the README. */
static int resource_matches(const char *id, const char *name, const char *query) {
    if (strcasecmp(id, query) == 0) return 1;
    if (strcasecmp(name, query) == 0) return 1;
    if (strcasecmp(local_part(id), query) == 0) return 1;
    if (ci_contains(name, query)) return 1;
    if (ci_contains(local_part(id), query)) return 1;
    return 0;
}

int world_item_matches_query(const item_t *it, const char *query) {
    if (!query || !query[0]) return 0;
    return resource_matches(it->id, it->name, query);
}

room_t *world_find_room(world_t *w, const char *id) {
    if (!id || !id[0]) return NULL;
    for (int i = 0; i < w->room_count; i++)
        if (strcmp(w->rooms[i].id, id) == 0) return &w->rooms[i];
    return NULL;
}

item_t *world_find_item(world_t *w, const char *id_or_name) {
    if (!id_or_name || !id_or_name[0]) return NULL;
    for (int i = 0; i < w->item_count; i++)
        if (resource_matches(w->items[i].id, w->items[i].name, id_or_name))
            return &w->items[i];
    return NULL;
}

npc_t *world_find_npc(world_t *w, const char *id_or_name) {
    if (!id_or_name || !id_or_name[0]) return NULL;
    for (int i = 0; i < w->npc_count; i++)
        if (resource_matches(w->npcs[i].id, w->npcs[i].name, id_or_name))
            return &w->npcs[i];
    return NULL;
}

item_t *world_find_item_in_room(world_t *w, const char *room_id, const char *id_or_name) {
    if (!id_or_name || !id_or_name[0]) return NULL;
    for (int i = 0; i < w->item_count; i++)
        if (strcmp(w->items[i].room, room_id) == 0 && resource_matches(w->items[i].id, w->items[i].name, id_or_name))
            return &w->items[i];
    return NULL;
}

npc_t *world_find_npc_in_room(world_t *w, const char *room_id, const char *id_or_name) {
    if (!id_or_name || !id_or_name[0]) return NULL;
    for (int i = 0; i < w->npc_count; i++) {
        npc_t *n = &w->npcs[i];
        if (strcmp(n->room, room_id) == 0 && (n->role != ROLE_ENEMY || n->alive) &&
            resource_matches(n->id, n->name, id_or_name))
            return n;
    }
    return NULL;
}
