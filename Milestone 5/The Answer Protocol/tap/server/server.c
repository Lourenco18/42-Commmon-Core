/* server.c - TAP protocol server (RFC 42TAP).
 *
 * Architecture: single-threaded, select()-based reactor. All world state
 * (players, world) lives in plain global structs with no locking needed,
 * since there is only ever one thread touching them. This keeps the
 * command handlers simple and avoids an entire class of concurrency bugs,
 * at the cost of not using multiple CPU cores - a reasonable trade-off for
 * a small line-based text protocol where handlers are cheap (see README
 * "Architecture" section for the full justification).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <signal.h>
#include <stdarg.h>
#include <ctype.h>

#include "world.h"
#include "../common/jsonmin.h"
#include "../common/log.h"

#define MAX_CLIENTS 128
#define BUF_SIZE 4096
#define MAX_LINE 1024
#define MAX_INVENTORY 32
#define MAX_QUESTS_PER_PLAYER 8
#define MAX_KILLS_PER_PLAYER 32
#define RATE_WINDOW_SECS 5
#define RATE_LIMIT_COMMANDS 30
#define RESPAWN_HP 50

typedef struct {
    char quest_id[ID_LEN];
    char giver[ID_LEN];
    int completed;
} quest_state_t;

typedef struct {
    char npc_id[ID_LEN];
    int count;
} kill_count_t;

typedef struct {
    int fd;
    int in_use;
    int authenticated;
    char username[NAME_LEN];
    char ip[INET_ADDRSTRLEN];
    char room[ID_LEN];

    char inventory[MAX_INVENTORY][ID_LEN];
    int inv_count;

    int hp, max_hp;
    int in_combat;
    char combat_target[ID_LEN];
    int defending;

    char group[ID_LEN]; /* empty = no group */

    quest_state_t quests[MAX_QUESTS_PER_PLAYER];
    int quest_count;

    kill_count_t kills[MAX_KILLS_PER_PLAYER];
    int kill_count;

    char inbuf[BUF_SIZE];
    size_t inlen;

    /* simple sliding-window rate limiting for abuse detection */
    time_t rate_window_start;
    int rate_count;
} player_t;

static player_t g_players[MAX_CLIENTS];
static world_t g_world;
static int g_listen_fd;
static int g_group_counter = 1;
static volatile sig_atomic_t g_running = 1;

static void on_sigint(int sig) { (void)sig; g_running = 0; }

/* ---------------- low-level send helper ---------------- */

static void send_raw(player_t *p, const char *line) {
    size_t len = strlen(line);
    size_t sent = 0;
    while (sent < len) {
        ssize_t n = send(p->fd, line + sent, len - sent, 0);
        if (n <= 0) {
            if (errno == EINTR) continue;
            log_line(LOG_ERROR, "send_failed", "\"player\":\"%s\",\"error\":\"%s\"", p->username, strerror(errno));
            return;
        }
        sent += (size_t)n;
    }
}

static void sendf(player_t *p, const char *fmt, ...) {
    char buf[BUF_SIZE];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    strncat(buf, "\n", sizeof(buf) - strlen(buf) - 1);
    send_raw(p, buf);
    log_line(LOG_INFO, "response_sent", "\"player\":\"%s\",\"line\":\"%.200s\"", p->username[0] ? p->username : "-", buf);
}

/* ---------------- player lookup / iteration ---------------- */

static player_t *find_by_username(const char *name) {
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (g_players[i].in_use && g_players[i].authenticated && strcasecmp(g_players[i].username, name) == 0)
            return &g_players[i];
    return NULL;
}

static int count_authenticated(void) {
    int c = 0;
    for (int i = 0; i < MAX_CLIENTS; i++) if (g_players[i].in_use && g_players[i].authenticated) c++;
    return c;
}

/* ---------------- broadcast helpers ---------------- */

static void broadcast_room(const char *room_id, int exclude_fd, const char *line) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        player_t *p = &g_players[i];
        if (p->in_use && p->authenticated && p->fd != exclude_fd && strcmp(p->room, room_id) == 0)
            send_raw(p, line);
    }
}

static void broadcast_global(int exclude_fd, const char *line) {
    for (int i = 0; i < MAX_CLIENTS; i++) {
        player_t *p = &g_players[i];
        if (p->in_use && p->authenticated && p->fd != exclude_fd)
            send_raw(p, line);
    }
}

static void broadcast_group(const char *group_id, int exclude_fd, const char *line) {
    if (!group_id[0]) return;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        player_t *p = &g_players[i];
        if (p->in_use && p->authenticated && p->fd != exclude_fd && strcmp(p->group, group_id) == 0)
            send_raw(p, line);
    }
}

static void broadcast_stats(void) {
    char line[128];
    snprintf(line, sizeof(line), "EVT STATS players=%d\n", count_authenticated());
    broadcast_global(-1, line);
}

/* ---------------- inventory helpers ---------------- */

static int inv_find(player_t *p, const char *id_or_name) {
    for (int i = 0; i < p->inv_count; i++) {
        item_t *it = world_find_item(&g_world, p->inventory[i]);
        if (it && world_item_matches_query(it, id_or_name)) return i;
    }
    return -1;
}

static int inv_count_item(player_t *p, const char *item_id) {
    int n = 0;
    for (int i = 0; i < p->inv_count; i++)
        if (strcmp(p->inventory[i], item_id) == 0) n++;
    return n;
}

static void inv_remove_at(player_t *p, int idx) {
    for (int i = idx; i < p->inv_count - 1; i++)
        strcpy(p->inventory[i], p->inventory[i + 1]);
    p->inv_count--;
}

static void inv_remove_one(player_t *p, const char *item_id) {
    for (int i = 0; i < p->inv_count; i++) {
        if (strcmp(p->inventory[i], item_id) == 0) { inv_remove_at(p, i); return; }
    }
}

/* ---------------- quest helpers ---------------- */

static quest_state_t *quest_find(player_t *p, const char *quest_id) {
    for (int i = 0; i < p->quest_count; i++)
        if (strcmp(p->quests[i].quest_id, quest_id) == 0) return &p->quests[i];
    return NULL;
}

static int kills_get(player_t *p, const char *npc_id) {
    for (int i = 0; i < p->kill_count; i++)
        if (strcmp(p->kills[i].npc_id, npc_id) == 0) return p->kills[i].count;
    return 0;
}

static void kills_inc(player_t *p, const char *npc_id) {
    for (int i = 0; i < p->kill_count; i++)
        if (strcmp(p->kills[i].npc_id, npc_id) == 0) { p->kills[i].count++; return; }
    if (p->kill_count < MAX_KILLS_PER_PLAYER) {
        snprintf(p->kills[p->kill_count].npc_id, ID_LEN, "%s", npc_id);
        p->kills[p->kill_count].count = 1;
        p->kill_count++;
    }
}

/* ---------------- LOOK / room JSON ---------------- */

static void build_look_json(sbuf_t *sb, player_t *self) {
    room_t *r = world_find_room(&g_world, self->room);
    sb_append(sb, "{\"room\":{");
    sb_append(sb, "\"id\":"); sb_append_json_string(sb, r->id); sb_append(sb, ",");
    sb_append(sb, "\"name\":"); sb_append_json_string(sb, r->name); sb_append(sb, ",");
    sb_append(sb, "\"description\":"); sb_append_json_string(sb, r->description); sb_append(sb, ",");
    sb_append(sb, "\"exits\":{");
    for (int i = 0; i < r->exit_count; i++) {
        if (i) sb_append(sb, ",");
        sb_append_json_string(sb, r->exits[i].direction);
        sb_append(sb, ":");
        sb_append_json_string(sb, r->exits[i].target);
    }
    sb_append(sb, "}},");

    sb_append(sb, "\"players\":[");
    int first = 1;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        player_t *p = &g_players[i];
        if (p->in_use && p->authenticated && strcmp(p->room, self->room) == 0) {
            if (!first) sb_append(sb, ",");
            sb_append_json_string(sb, p->username);
            first = 0;
        }
    }
    sb_append(sb, "],\"items\":[");
    first = 1;
    for (int i = 0; i < g_world.item_count; i++) {
        if (strcmp(g_world.items[i].room, self->room) == 0) {
            if (!first) sb_append(sb, ",");
            sb_append_json_string(sb, g_world.items[i].id);
            first = 0;
        }
    }
    sb_append(sb, "],\"npcs\":[");
    first = 1;
    for (int i = 0; i < g_world.npc_count; i++) {
        npc_t *n = &g_world.npcs[i];
        if (strcmp(n->room, self->room) == 0 && (n->role != ROLE_ENEMY || n->alive)) {
            if (!first) sb_append(sb, ",");
            sb_append_json_string(sb, n->id);
            first = 0;
        }
    }
    sb_append(sb, "]}");
}

/* ---------------- respawn ---------------- */

static void respawn(player_t *p) {
    char leave[MAX_LINE];
    snprintf(leave, sizeof(leave), "EVT ROOM PRESENCE LEAVE %s\n", p->username);
    broadcast_room(p->room, p->fd, leave);
    snprintf(p->room, sizeof(p->room), "%s", g_world.start_room);
    p->hp = RESPAWN_HP;
    p->in_combat = 0;
    p->defending = 0;
    char enter[MAX_LINE];
    snprintf(enter, sizeof(enter), "EVT ROOM PRESENCE ENTER %s\n", p->username);
    broadcast_room(p->room, p->fd, enter);
    log_line(LOG_INFO, "respawn", "\"player\":\"%s\",\"room\":\"%s\",\"hp\":%d", p->username, p->room, p->hp);
}

/* ---------------- command handlers ---------------- */

static void cmd_connect(player_t *p, const char *arg) {
    if (p->authenticated) { sendf(p, "ERR 905 ALREADY_AUTHENTICATED"); return; }
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    char name[NAME_LEN];
    snprintf(name, sizeof(name), "%s", arg);
    if (find_by_username(name)) {
        sendf(p, "ERR 201 NAME_IN_USE");
        log_line(LOG_WARN, "connect_rejected", "\"reason\":\"name_in_use\",\"name\":\"%s\",\"ip\":\"%s\"", name, p->ip);
        return;
    }
    snprintf(p->username, sizeof(p->username), "%s", name);
    p->authenticated = 1;
    snprintf(p->room, sizeof(p->room), "%s", g_world.start_room);
    p->hp = 100; p->max_hp = 100;
    sendf(p, "OK connected");
    log_line(LOG_INFO, "connect", "\"player\":\"%s\",\"ip\":\"%s\"", p->username, p->ip);
    char enter[MAX_LINE];
    snprintf(enter, sizeof(enter), "EVT ROOM PRESENCE ENTER %s\n", p->username);
    broadcast_room(p->room, p->fd, enter);
    broadcast_stats();
}

static void cmd_look(player_t *p) {
    sbuf_t sb; sb_init(&sb);
    build_look_json(&sb, p);
    sendf(p, "OK %s", sb.data);
    sb_free(&sb);
}

static void cmd_move(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    room_t *r = world_find_room(&g_world, p->room);
    const char *target = NULL;
    for (int i = 0; i < r->exit_count; i++)
        if (strcasecmp(r->exits[i].direction, arg) == 0) { target = r->exits[i].target; break; }
    if (!target) { sendf(p, "ERR 301 NO_EXIT"); return; }

    char leave[MAX_LINE];
    snprintf(leave, sizeof(leave), "EVT ROOM PRESENCE LEAVE %s\n", p->username);
    broadcast_room(p->room, p->fd, leave);

    snprintf(p->room, sizeof(p->room), "%s", target);

    char enter[MAX_LINE];
    snprintf(enter, sizeof(enter), "EVT ROOM PRESENCE ENTER %s\n", p->username);
    broadcast_room(p->room, p->fd, enter);

    sendf(p, "OK room=%s", p->room);
    log_line(LOG_INFO, "move", "\"player\":\"%s\",\"room\":\"%s\"", p->username, p->room);
}

static void cmd_chat(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    char scope[16] = {0};
    const char *msg = NULL;
    const char *sp = strchr(arg, ' ');
    if (sp) {
        size_t n = (size_t)(sp - arg);
        if (n >= sizeof(scope)) n = sizeof(scope) - 1;
        memcpy(scope, arg, n); scope[n] = '\0';
        msg = sp + 1;
    } else {
        snprintf(scope, sizeof(scope), "%s", arg);
        msg = "";
    }
    for (char *c = scope; *c; c++) *c = (char)toupper((unsigned char)*c);

    if (strcmp(scope, "GROUP") == 0 && !p->group[0]) { sendf(p, "ERR 401 NOT_IN_GROUP"); return; }
    if (strcmp(scope, "GLOBAL") != 0 && strcmp(scope, "ROOM") != 0 && strcmp(scope, "GROUP") != 0) {
        sendf(p, "ERR 903 BAD_ARGS"); return;
    }

    sendf(p, "OK");
    char line[MAX_LINE];
    snprintf(line, sizeof(line), "EVT %s CHAT %s %s\n", scope, p->username, msg);
    if (strcmp(scope, "GLOBAL") == 0) broadcast_global(-1, line);
    else if (strcmp(scope, "ROOM") == 0) broadcast_room(p->room, -1, line);
    else broadcast_group(p->group, -1, line);
    log_line(LOG_INFO, "chat", "\"player\":\"%s\",\"scope\":\"%s\",\"message\":\"%.100s\"", p->username, scope, msg);
}

static void cmd_take(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    item_t *it = world_find_item_in_room(&g_world, p->room, arg);
    if (!it || !it->obtainable) { sendf(p, "ERR 404 ITEM_NOT_FOUND"); return; }
    if (p->inv_count >= MAX_INVENTORY) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    snprintf(p->inventory[p->inv_count++], ID_LEN, "%s", it->id);
    it->room[0] = '\0'; /* removed from room: no duplication */
    sendf(p, "OK taken=%s", it->id);
    log_line(LOG_INFO, "item_taken", "\"player\":\"%s\",\"item\":\"%s\"", p->username, it->id);
}

static void cmd_drop(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    int idx = inv_find(p, arg);
    if (idx < 0) { sendf(p, "ERR 404 ITEM_NOT_IN_INVENTORY"); return; }
    item_t *it = world_find_item(&g_world, p->inventory[idx]);
    snprintf(it->room, sizeof(it->room), "%s", p->room);
    sendf(p, "OK dropped=%s", it->id);
    inv_remove_at(p, idx);
    log_line(LOG_INFO, "item_dropped", "\"player\":\"%s\",\"item\":\"%s\"", p->username, it->id);
}

static void cmd_inventory(player_t *p) {
    sbuf_t sb; sb_init(&sb);
    sb_append(&sb, "[");
    for (int i = 0; i < p->inv_count; i++) {
        if (i) sb_append(&sb, ",");
        sb_append_json_string(&sb, p->inventory[i]);
    }
    sb_append(&sb, "]");
    sendf(p, "OK %s", sb.data);
    sb_free(&sb);
}

static void cmd_talk(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    npc_t *n = world_find_npc_in_room(&g_world, p->room, arg);
    if (!n) { sendf(p, "ERR 404 NPC_NOT_FOUND"); return; }
    const char *line = n->dialogue_count > 0 ? n->dialogue[n->dialogue_next] : "...";
    if (n->dialogue_count > 0) n->dialogue_next = (n->dialogue_next + 1) % n->dialogue_count;
    sendf(p, "OK %s", line);
    log_line(LOG_INFO, "npc_talk", "\"player\":\"%s\",\"npc\":\"%s\"", p->username, n->id);
}

static const char *status_word(player_t *p) {
    if (p->in_combat) return "in_combat";
    if (p->hp <= 0) return "defeated";
    if (p->hp < p->max_hp * 3 / 10) return "critical";
    if (p->hp < p->max_hp * 7 / 10) return "wounded";
    return "healthy";
}

static void cmd_status(player_t *p) {
    sendf(p, "OK {\"hp\":%d,\"max_hp\":%d,\"status\":\"%s\"}", p->hp, p->max_hp, status_word(p));
}

static void cmd_attack(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    npc_t *n = world_find_npc(&g_world, arg);
    if (!n || strcmp(n->room, p->room) != 0) { sendf(p, "ERR 404 NPC_NOT_FOUND"); return; }
    if (n->role != ROLE_ENEMY) { sendf(p, "ERR 405 NPC_NOT_HOSTILE"); return; }
    if (!n->alive) { sendf(p, "ERR 404 NPC_NOT_FOUND"); return; }

    p->in_combat = 1;
    snprintf(p->combat_target, sizeof(p->combat_target), "%s", n->id);

    int damage = 8 + rand() % 8; /* 8-15 */
    n->hp -= damage;
    const char *status;
    int counter = 0;

    if (n->hp <= 0) {
        n->hp = 0;
        n->alive = 0;
        p->in_combat = 0;
        kills_inc(p, n->id);
        status = "victory";
        char line[MAX_LINE];
        snprintf(line, sizeof(line), "EVT ROOM CHAT server %s has defeated %s!\n", p->username, n->name);
        broadcast_room(p->room, -1, line);
        log_line(LOG_INFO, "combat_victory", "\"player\":\"%s\",\"npc\":\"%s\",\"damage\":%d", p->username, n->id, damage);
    } else {
        counter = 3 + rand() % 8; /* 3-10 */
        if (p->defending) { counter /= 2; p->defending = 0; }
        p->hp -= counter;
        if (p->hp <= 0) {
            status = "defeated";
            sendf(p, "OK {\"attacker_hp\":%d,\"target_hp\":%d,\"damage\":%d,\"counter_damage\":%d,\"status\":\"%s\"}",
                  0, n->hp, damage, counter, status);
            log_line(LOG_WARN, "combat_defeat", "\"player\":\"%s\",\"npc\":\"%s\"", p->username, n->id);
            respawn(p);
            return;
        }
        status = "combat";
        log_line(LOG_INFO, "combat_round", "\"player\":\"%s\",\"npc\":\"%s\",\"damage\":%d,\"counter_damage\":%d", p->username, n->id, damage, counter);
    }
    sendf(p, "OK {\"attacker_hp\":%d,\"target_hp\":%d,\"damage\":%d,\"counter_damage\":%d,\"status\":\"%s\"}",
          p->hp, n->hp, damage, counter, status);
}

/* Extension commands: DEFEND and FLEE (documented in README). */
static void cmd_defend(player_t *p) {
    if (!p->in_combat) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    p->defending = 1;
    sendf(p, "OK {\"status\":\"defending\"}");
}

static void cmd_flee(player_t *p) {
    if (!p->in_combat) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    if (rand() % 2 == 0) {
        p->in_combat = 0;
        sendf(p, "OK {\"status\":\"fled\"}");
        log_line(LOG_INFO, "combat_flee", "\"player\":\"%s\",\"result\":\"escaped\"", p->username);
    } else {
        int dmg = 5 + rand() % 6;
        p->hp -= dmg;
        p->in_combat = 0;
        if (p->hp <= 0) {
            sendf(p, "OK {\"status\":\"fled_damaged\",\"hp\":0}");
            log_line(LOG_WARN, "combat_flee", "\"player\":\"%s\",\"result\":\"defeated\"", p->username);
            respawn(p);
            return;
        }
        sendf(p, "OK {\"status\":\"fled_damaged\",\"hp\":%d}", p->hp);
        log_line(LOG_INFO, "combat_flee", "\"player\":\"%s\",\"result\":\"damaged\",\"hp\":%d", p->username, p->hp);
    }
}

static void cmd_quest(player_t *p, const char *arg) {
    if (!arg || !arg[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
    npc_t *n = world_find_npc(&g_world, arg);
    if (!n || strcmp(n->room, p->room) != 0 || !n->quest.active) { sendf(p, "ERR 404 NPC_NOT_FOUND"); return; }

    quest_state_t *qs = quest_find(p, n->quest.id);
    if (!qs) {
        if (p->quest_count >= MAX_QUESTS_PER_PLAYER) { sendf(p, "ERR 903 BAD_ARGS"); return; }
        qs = &p->quests[p->quest_count++];
        snprintf(qs->quest_id, ID_LEN, "%s", n->quest.id);
        snprintf(qs->giver, ID_LEN, "%s", n->id);
        qs->completed = 0;
        sendf(p, "OK {\"quest_id\":\"%s\",\"description\":\"%s\",\"reward\":\"%s\",\"status\":\"available\"}",
              n->quest.id, n->quest.description, n->quest.reward_item);
        log_line(LOG_INFO, "quest_assigned", "\"player\":\"%s\",\"quest\":\"%s\"", p->username, n->quest.id);
        return;
    }
    if (qs->completed) { sendf(p, "ERR 406 NO_QUEST_AVAILABLE"); return; }

    /* Check completion */
    int done = 0;
    if (n->quest.require_item[0]) {
        done = inv_count_item(p, n->quest.require_item) >= n->quest.require_count;
    } else if (n->quest.require_kill[0]) {
        done = kills_get(p, n->quest.require_kill) >= n->quest.require_count;
    }

    if (done) {
        if (n->quest.require_item[0]) {
            for (int i = 0; i < n->quest.require_count; i++) inv_remove_one(p, n->quest.require_item);
        }
        if (n->quest.reward_item[0] && p->inv_count < MAX_INVENTORY) {
            snprintf(p->inventory[p->inv_count++], ID_LEN, "%s", n->quest.reward_item);
        }
        qs->completed = 1;
        sendf(p, "OK {\"quest_id\":\"%s\",\"status\":\"completed\",\"reward\":\"%s\"}", n->quest.id, n->quest.reward_item);
        log_line(LOG_INFO, "quest_completed", "\"player\":\"%s\",\"quest\":\"%s\",\"reward\":\"%s\"", p->username, n->quest.id, n->quest.reward_item);
    } else {
        int progress_have = n->quest.require_item[0] ? inv_count_item(p, n->quest.require_item) : kills_get(p, n->quest.require_kill);
        sendf(p, "OK {\"quest_id\":\"%s\",\"status\":\"active\",\"progress\":\"%d/%d\"}",
              n->quest.id, progress_have, n->quest.require_count);
    }
}

static void cmd_quests(player_t *p) {
    sbuf_t sb; sb_init(&sb);
    sb_append(&sb, "[");
    for (int i = 0; i < p->quest_count; i++) {
        if (i) sb_append(&sb, ",");
        quest_state_t *qs = &p->quests[i];
        if (qs->completed) {
            sb_appendf(&sb, "{\"quest_id\":\"%s\",\"status\":\"completed\"}", qs->quest_id);
        } else {
            npc_t *n = world_find_npc(&g_world, qs->giver);
            int have = 0, need = 1;
            if (n) {
                need = n->quest.require_count;
                have = n->quest.require_item[0] ? inv_count_item(p, n->quest.require_item) : kills_get(p, n->quest.require_kill);
            }
            sb_appendf(&sb, "{\"quest_id\":\"%s\",\"status\":\"active\",\"progress\":\"%d/%d\"}", qs->quest_id, have, need);
        }
    }
    sb_append(&sb, "]");
    sendf(p, "OK %s", sb.data);
    sb_free(&sb);
}

/* Documented deviation: RFC 5.2.2 specifies a bare "OK players=<n>" reply
 * for WHO, but section V.5 of the assignment's example interactions shows
 * a richer JSON reply with room + server counts, which is what the GUI
 * client needs (see README "Protocol Implementation" for justification).
 */
static void cmd_who(player_t *p) {
    sbuf_t sb; sb_init(&sb);
    sb_append(&sb, "{\"room\":[");
    int first = 1;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        player_t *o = &g_players[i];
        if (o->in_use && o->authenticated && strcmp(o->room, p->room) == 0) {
            if (!first) sb_append(&sb, ",");
            sb_append_json_string(&sb, o->username);
            first = 0;
        }
    }
    sb_appendf(&sb, "],\"server\":%d}", count_authenticated());
    sendf(p, "OK %s", sb.data);
    sb_free(&sb);
}

static void cmd_group(player_t *p, const char *arg) {
    char sub[16] = {0};
    const char *rest = NULL;
    if (arg) {
        const char *sp = strchr(arg, ' ');
        if (sp) {
            size_t n = (size_t)(sp - arg);
            if (n >= sizeof(sub)) n = sizeof(sub) - 1;
            memcpy(sub, arg, n); sub[n] = '\0';
            rest = sp + 1;
        } else {
            snprintf(sub, sizeof(sub), "%s", arg);
        }
    }
    for (char *c = sub; *c; c++) *c = (char)toupper((unsigned char)*c);

    if (strcmp(sub, "CREATE") == 0) {
        if (p->group[0]) { sendf(p, "ERR 402 ALREADY_IN_GROUP"); return; }
        snprintf(p->group, sizeof(p->group), "group.%d", g_group_counter++);
        sendf(p, "OK group=%s", p->group);
        log_line(LOG_INFO, "group_created", "\"player\":\"%s\",\"group\":\"%s\"", p->username, p->group);
    } else if (strcmp(sub, "INVITE") == 0) {
        if (!p->group[0]) { sendf(p, "ERR 401 NOT_IN_GROUP"); return; }
        if (!rest || !rest[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
        player_t *target = find_by_username(rest);
        if (!target) { sendf(p, "ERR 407 PLAYER_NOT_FOUND"); return; }
        sendf(p, "OK");
        char line[MAX_LINE];
        snprintf(line, sizeof(line), "EVT GROUP INVITE %s\n", p->username);
        send_raw(target, line);
        log_line(LOG_INFO, "group_invite", "\"player\":\"%s\",\"target\":\"%s\",\"group\":\"%s\"", p->username, target->username, p->group);
    } else if (strcmp(sub, "JOIN") == 0) {
        if (p->group[0]) { sendf(p, "ERR 402 ALREADY_IN_GROUP"); return; }
        if (!rest || !rest[0]) { sendf(p, "ERR 903 BAD_ARGS"); return; }
        int exists = 0;
        for (int i = 0; i < MAX_CLIENTS; i++)
            if (g_players[i].in_use && g_players[i].authenticated && strcmp(g_players[i].group, rest) == 0) exists = 1;
        if (!exists) { sendf(p, "ERR 903 BAD_ARGS"); return; }
        snprintf(p->group, sizeof(p->group), "%s", rest);
        sendf(p, "OK group=%s", p->group);
        char line[MAX_LINE];
        snprintf(line, sizeof(line), "EVT GROUP JOIN %s\n", p->username);
        broadcast_group(p->group, p->fd, line);
        log_line(LOG_INFO, "group_join", "\"player\":\"%s\",\"group\":\"%s\"", p->username, p->group);
    } else if (strcmp(sub, "LEAVE") == 0) {
        if (!p->group[0]) { sendf(p, "ERR 401 NOT_IN_GROUP"); return; }
        char line[MAX_LINE];
        snprintf(line, sizeof(line), "EVT GROUP LEAVE %s\n", p->username);
        broadcast_group(p->group, p->fd, line);
        log_line(LOG_INFO, "group_leave", "\"player\":\"%s\",\"group\":\"%s\"", p->username, p->group);
        p->group[0] = '\0';
        sendf(p, "OK");
    } else {
        sendf(p, "ERR 902 UNKNOWN_COMMAND");
    }
}

static void disconnect_player(player_t *p, const char *reason);

static void cmd_quit(player_t *p) {
    sendf(p, "OK bye");
    disconnect_player(p, "quit");
}

/* ---------------- dispatch ---------------- */

static void trim(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\r' || s[n - 1] == '\n' || s[n - 1] == ' ')) s[--n] = '\0';
    char *start = s;
    while (*start == ' ') start++;
    if (start != s) memmove(s, start, strlen(start) + 1);
}

static int check_rate_limit(player_t *p) {
    time_t now = time(NULL);
    if (now - p->rate_window_start >= RATE_WINDOW_SECS) {
        p->rate_window_start = now;
        p->rate_count = 0;
    }
    p->rate_count++;
    if (p->rate_count > RATE_LIMIT_COMMANDS) {
        log_line(LOG_WARN, "abuse_detected", "\"player\":\"%s\",\"ip\":\"%s\",\"commands_in_window\":%d",
                 p->username[0] ? p->username : "-", p->ip, p->rate_count);
        return 0;
    }
    return 1;
}

static void dispatch(player_t *p, char *line) {
    trim(line);
    if (!line[0]) return;

    log_line(LOG_INFO, "command_received", "\"player\":\"%s\",\"ip\":\"%s\",\"line\":\"%.200s\"",
             p->username[0] ? p->username : "-", p->ip, line);

    if (!check_rate_limit(p)) {
        sendf(p, "ERR 908 RATE_LIMITED");
        return;
    }

    char *sp = strchr(line, ' ');
    char verb[32];
    char *arg = NULL;
    if (sp) {
        size_t n = (size_t)(sp - line);
        if (n >= sizeof(verb)) n = sizeof(verb) - 1;
        memcpy(verb, line, n); verb[n] = '\0';
        arg = sp + 1;
        while (*arg == ' ') arg++;
    } else {
        snprintf(verb, sizeof(verb), "%s", line);
    }
    for (char *c = verb; *c; c++) *c = (char)toupper((unsigned char)*c);

    if (strcmp(verb, "CONNECT") == 0) { cmd_connect(p, arg); return; }
    if (!p->authenticated) { sendf(p, "ERR 904 NOT_AUTHENTICATED"); return; }

    if (strcmp(verb, "LOOK") == 0) cmd_look(p);
    else if (strcmp(verb, "MOVE") == 0) cmd_move(p, arg);
    else if (strcmp(verb, "CHAT") == 0) cmd_chat(p, arg);
    else if (strcmp(verb, "TAKE") == 0) cmd_take(p, arg);
    else if (strcmp(verb, "DROP") == 0) cmd_drop(p, arg);
    else if (strcmp(verb, "INVENTORY") == 0) cmd_inventory(p);
    else if (strcmp(verb, "TALK") == 0) cmd_talk(p, arg);
    else if (strcmp(verb, "ATTACK") == 0) cmd_attack(p, arg);
    else if (strcmp(verb, "DEFEND") == 0) cmd_defend(p);
    else if (strcmp(verb, "FLEE") == 0) cmd_flee(p);
    else if (strcmp(verb, "STATUS") == 0) cmd_status(p);
    else if (strcmp(verb, "QUEST") == 0) cmd_quest(p, arg);
    else if (strcmp(verb, "QUESTS") == 0) cmd_quests(p);
    else if (strcmp(verb, "WHO") == 0) cmd_who(p);
    else if (strcmp(verb, "GROUP") == 0) cmd_group(p, arg);
    else if (strcmp(verb, "QUIT") == 0) cmd_quit(p);
    else sendf(p, "ERR 902 UNKNOWN_COMMAND");
}

/* ---------------- connection lifecycle ---------------- */

static void disconnect_player(player_t *p, const char *reason) {
    if (p->authenticated) {
        char leave[MAX_LINE];
        snprintf(leave, sizeof(leave), "EVT ROOM PRESENCE LEAVE %s\n", p->username);
        broadcast_room(p->room, p->fd, leave);
        if (p->group[0]) {
            char gl[MAX_LINE];
            snprintf(gl, sizeof(gl), "EVT GROUP LEAVE %s\n", p->username);
            broadcast_group(p->group, p->fd, gl);
        }
        /* return held items to their last room so they are not lost */
        for (int i = 0; i < p->inv_count; i++) {
            item_t *it = world_find_item(&g_world, p->inventory[i]);
            if (it) snprintf(it->room, sizeof(it->room), "%s", p->room);
        }
        log_line(LOG_INFO, "disconnect", "\"player\":\"%s\",\"ip\":\"%s\",\"reason\":\"%s\"", p->username, p->ip, reason);
    }
    close(p->fd);
    memset(p, 0, sizeof(*p));
    p->in_use = 0;
    broadcast_stats();
}

static player_t *alloc_player(void) {
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (!g_players[i].in_use) return &g_players[i];
    return NULL;
}

static void handle_accept(void) {
    struct sockaddr_in addr;
    socklen_t alen = sizeof(addr);
    int fd = accept(g_listen_fd, (struct sockaddr *)&addr, &alen);
    if (fd < 0) return;

    player_t *p = alloc_player();
    if (!p) {
        const char *msg = "ERR 900 CONNECTION_FAILED\n";
        send(fd, msg, strlen(msg), 0);
        close(fd);
        return;
    }
    memset(p, 0, sizeof(*p));
    p->fd = fd;
    p->in_use = 1;
    p->rate_window_start = time(NULL);
    inet_ntop(AF_INET, &addr.sin_addr, p->ip, sizeof(p->ip));

    int one = 1;
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

    log_line(LOG_INFO, "tcp_connect", "\"ip\":\"%s\",\"fd\":%d", p->ip, fd);
    send_raw(p, "OK hello proto=1\n");
}

static void handle_readable(player_t *p) {
    char chunk[BUF_SIZE];
    ssize_t n = recv(p->fd, chunk, sizeof(chunk) - 1, 0);
    if (n <= 0) {
        disconnect_player(p, n == 0 ? "closed" : "error");
        return;
    }
    chunk[n] = '\0';

    if (p->inlen + (size_t)n >= sizeof(p->inbuf)) {
        /* line too long / flooding: reset buffer defensively */
        p->inlen = 0;
        sendf(p, "ERR 903 BAD_ARGS");
        return;
    }
    memcpy(p->inbuf + p->inlen, chunk, (size_t)n + 1);
    p->inlen += (size_t)n;

    /* Process every complete (\n-terminated) line in the buffer. Handles
     * both fragmentation (partial line stays buffered) and coalescing
     * (multiple lines in one recv). */
    char *start = p->inbuf;
    char *nl;
    while ((nl = strchr(start, '\n')) != NULL) {
        *nl = '\0';
        char line_copy[MAX_LINE];
        snprintf(line_copy, sizeof(line_copy), "%s", start);
        dispatch(p, line_copy);
        if (!p->in_use) return; /* QUIT / error may have freed this slot */
        start = nl + 1;
    }
    size_t remaining = strlen(start);
    memmove(p->inbuf, start, remaining + 1);
    p->inlen = remaining;
}

int main(int argc, char **argv) {
    int port = 4242;
    const char *world_path = "world/world.json";
    const char *log_path = "logs/server.log";

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--port") == 0 && i + 1 < argc) port = atoi(argv[++i]);
        else if (strcmp(argv[i], "--world") == 0 && i + 1 < argc) world_path = argv[++i];
        else if (strcmp(argv[i], "--log") == 0 && i + 1 < argc) log_path = argv[++i];
        else if (strcmp(argv[i], "--help") == 0) {
            printf("usage: %s [--port N] [--world path] [--log path]\n", argv[0]);
            return 0;
        }
    }

    srand((unsigned)time(NULL));
    log_init(log_path);

    if (world_load(&g_world, world_path) != 0) {
        fprintf(stderr, "fatal: failed to load world from '%s'\n", world_path);
        return 1;
    }
    log_line(LOG_INFO, "world_loaded", "\"rooms\":%d,\"items\":%d,\"npcs\":%d,\"path\":\"%s\"",
             g_world.room_count, g_world.item_count, g_world.npc_count, world_path);

    signal(SIGINT, on_sigint);
    signal(SIGTERM, on_sigint);
    signal(SIGPIPE, SIG_IGN);

    g_listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (g_listen_fd < 0) { perror("socket"); return 1; }
    int opt = 1;
    setsockopt(g_listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons((uint16_t)port);

    if (bind(g_listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) { perror("bind"); return 1; }
    if (listen(g_listen_fd, 16) < 0) { perror("listen"); return 1; }

    log_line(LOG_INFO, "server_started", "\"port\":%d", port);
    printf("TAP server listening on port %d (world: %s)\n", port, world_path);

    while (g_running) {
        fd_set readfds;
        FD_ZERO(&readfds);
        FD_SET(g_listen_fd, &readfds);
        int maxfd = g_listen_fd;
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (g_players[i].in_use) {
                FD_SET(g_players[i].fd, &readfds);
                if (g_players[i].fd > maxfd) maxfd = g_players[i].fd;
            }
        }
        struct timeval tv = { .tv_sec = 1, .tv_usec = 0 };
        int ready = select(maxfd + 1, &readfds, NULL, NULL, &tv);
        if (ready < 0) {
            if (errno == EINTR) continue;
            perror("select");
            break;
        }
        if (ready == 0) continue;

        if (FD_ISSET(g_listen_fd, &readfds)) handle_accept();
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (g_players[i].in_use && FD_ISSET(g_players[i].fd, &readfds)) {
                handle_readable(&g_players[i]);
            }
        }
    }

    log_line(LOG_INFO, "server_stopping", NULL);
    for (int i = 0; i < MAX_CLIENTS; i++)
        if (g_players[i].in_use) close(g_players[i].fd);
    close(g_listen_fd);
    log_close();
    return 0;
}
