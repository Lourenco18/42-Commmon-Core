/* gui.c - TAP GTK3 GUI client.
 *
 * Networking is fully asynchronous: the socket is registered with the
 * GLib main loop via a GIOChannel watch (g_io_add_watch), so the UI never
 * blocks on recv() and keeps handling window events, button clicks, and
 * incoming EVT pushes at the same time (GUI requirement: "must remain
 * responsive while receiving asynchronous events").
 *
 * Because TAP responses ("OK ...204" / "ERR ...") don't repeat the
 * command that triggered them, this client keeps a small FIFO queue of
 * the verbs it has sent so it knows how to interpret each response as it
 * arrives (see `pending_push` / `pending_pop`).
 */
#include <gtk/gtk.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>

#include "../common/jsonmin.h"

#define NETBUF_SIZE 8192
#define PENDING_CAP 64

/* ---------------- pending-command queue ---------------- */
static char pending[PENDING_CAP][32];
static int pending_head = 0, pending_tail = 0;

static void pending_push(const char *verb) {
    if ((pending_tail + 1) % PENDING_CAP == pending_head) return; /* full: drop */
    snprintf(pending[pending_tail], sizeof(pending[0]), "%s", verb);
    pending_tail = (pending_tail + 1) % PENDING_CAP;
}

static int pending_pop(char *out, size_t outcap) {
    if (pending_head == pending_tail) return 0;
    snprintf(out, outcap, "%s", pending[pending_head]);
    pending_head = (pending_head + 1) % PENDING_CAP;
    return 1;
}

/* ---------------- app state ---------------- */

typedef struct {
    GtkWidget *window;

    /* connection bar */
    GtkWidget *host_entry, *port_entry, *username_entry, *connect_button;

    /* main area */
    GtkWidget *main_box;
    GtkWidget *room_name_label, *room_desc_label, *exits_box;
    GtkWidget *players_box, *items_box, *npcs_box;
    GtkWidget *inventory_box;
    GtkWidget *hp_label, *counts_label;

    GtkTextBuffer *chat_global, *chat_room, *chat_group;
    GtkWidget *chat_entry, *scope_combo;
    GtkTextBuffer *log_buffer;
    GtkWidget *log_view;

    GtkWidget *group_target_entry;

    int fd;
    GIOChannel *chan;
    guint watch_id;
    char netbuf[NETBUF_SIZE];
    size_t netlen;
    char current_room[128];
} App;

static App app;

/* ---------------- helpers ---------------- */

static void log_append(const char *fmt, ...) {
    char buf[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    GtkTextIter end;
    gtk_text_buffer_get_end_iter(app.log_buffer, &end);
    gtk_text_buffer_insert(app.log_buffer, &end, buf, -1);
    gtk_text_buffer_insert(app.log_buffer, &end, "\n", -1);
    GtkTextMark *mark = gtk_text_buffer_get_insert(app.log_buffer);
    gtk_text_view_scroll_to_mark(GTK_TEXT_VIEW(app.log_view), mark, 0.0, FALSE, 0, 0);
}

static void chat_append(GtkTextBuffer *buf, const char *fmt, ...) {
    char msg[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof(msg), fmt, ap);
    va_end(ap);
    GtkTextIter end;
    gtk_text_buffer_get_end_iter(buf, &end);
    gtk_text_buffer_insert(buf, &end, msg, -1);
    gtk_text_buffer_insert(buf, &end, "\n", -1);
}

static void clear_box(GtkWidget *box) {
    GList *children = gtk_container_get_children(GTK_CONTAINER(box));
    for (GList *it = children; it; it = it->next) gtk_widget_destroy(GTK_WIDGET(it->data));
    g_list_free(children);
}

/* Sends one protocol line and, unless this is a fire-and-forget verb
 * (currently none are), records it so the response can be interpreted. */
static void send_line(const char *line) {
    if (app.fd < 0) return;
    char withnl[1200];
    snprintf(withnl, sizeof(withnl), "%s\n", line);
    ssize_t n = send(app.fd, withnl, strlen(withnl), 0);
    if (n < 0) log_append("[error] send failed: %s", strerror(errno));
    log_append("> %s", line);

    char verb[32] = {0};
    const char *sp = strchr(line, ' ');
    size_t vlen = sp ? (size_t)(sp - line) : strlen(line);
    if (vlen >= sizeof(verb)) vlen = sizeof(verb) - 1;
    memcpy(verb, line, vlen);
    verb[vlen] = '\0';
    for (char *c = verb; *c; c++) *c = (char)g_ascii_toupper(*c);
    pending_push(verb);
}

static void send_linef(const char *fmt, ...) {
    char buf[1200];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    send_line(buf);
}

/* ---------------- room/inventory rendering ---------------- */

static void on_take_clicked(GtkButton *btn, gpointer data) {
    (void)btn;
    send_linef("TAKE %s", (const char *)data);
}
static void on_drop_clicked(GtkButton *btn, gpointer data) {
    (void)btn;
    send_linef("DROP %s", (const char *)data);
}
static void on_talk_clicked(GtkButton *btn, gpointer data) {
    (void)btn;
    send_linef("TALK %s", (const char *)data);
}
static void on_attack_clicked(GtkButton *btn, gpointer data) {
    (void)btn;
    send_linef("ATTACK %s", (const char *)data);
}
static void on_quest_clicked(GtkButton *btn, gpointer data) {
    (void)btn;
    send_linef("QUEST %s", (const char *)data);
}
static void on_move_clicked(GtkButton *btn, gpointer data) {
    (void)btn;
    send_linef("MOVE %s", (const char *)data);
}

/* GClosureNotify-compatible wrapper around g_free, used to release the
 * g_strdup'd ids we attach to dynamically created row buttons. */
static void free_closure_data(gpointer data, GClosure *closure) {
    (void)closure;
    g_free(data);
}

static GtkWidget *make_row(const char *text) {
    GtkWidget *row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    GtkWidget *label = gtk_label_new(text);
    gtk_label_set_xalign(GTK_LABEL(label), 0.0);
    gtk_widget_set_hexpand(label, TRUE);
    gtk_box_pack_start(GTK_BOX(row), label, TRUE, TRUE, 0);
    return row;
}

static void render_look_json(json_value_t *root) {
    json_value_t *room = json_obj_get(root, "room");
    const char *rid = json_as_str(json_obj_get(room, "id"));
    const char *rname = json_as_str(json_obj_get(room, "name"));
    const char *rdesc = json_as_str(json_obj_get(room, "description"));
    if (rid) snprintf(app.current_room, sizeof(app.current_room), "%s", rid);

    char titlebuf[256];
    snprintf(titlebuf, sizeof(titlebuf), "<b>%s</b>  <span size='small' foreground='gray'>(%s)</span>",
             rname ? rname : "?", rid ? rid : "?");
    gtk_label_set_markup(GTK_LABEL(app.room_name_label), titlebuf);
    gtk_label_set_text(GTK_LABEL(app.room_desc_label), rdesc ? rdesc : "");

    /* exits */
    clear_box(app.exits_box);
    json_value_t *exits = json_obj_get(room, "exits");
    if (exits && exits->type == JV_OBJ) {
        for (size_t i = 0; i < exits->u.obj.count; i++) {
            char label[64];
            snprintf(label, sizeof(label), "%s -> %s", exits->u.obj.keys[i], json_as_str(exits->u.obj.vals[i]));
            GtkWidget *btn = gtk_button_new_with_label(label);
            g_signal_connect_data(btn, "clicked", G_CALLBACK(on_move_clicked),
                                   g_strdup(exits->u.obj.keys[i]), free_closure_data, 0);
            gtk_box_pack_start(GTK_BOX(app.exits_box), btn, FALSE, FALSE, 0);
        }
    }
    gtk_widget_show_all(app.exits_box);

    /* players */
    clear_box(app.players_box);
    json_value_t *players = json_obj_get(root, "players");
    for (size_t i = 0; i < json_arr_len(players); i++) {
        const char *name = json_as_str(json_arr_get(players, i));
        gtk_box_pack_start(GTK_BOX(app.players_box), make_row(name ? name : "?"), FALSE, FALSE, 0);
    }
    gtk_widget_show_all(app.players_box);

    /* items with Take buttons */
    clear_box(app.items_box);
    json_value_t *items = json_obj_get(root, "items");
    for (size_t i = 0; i < json_arr_len(items); i++) {
        const char *id = json_as_str(json_arr_get(items, i));
        if (!id) continue;
        GtkWidget *row = make_row(id);
        GtkWidget *btn = gtk_button_new_with_label("Take");
        g_signal_connect_data(btn, "clicked", G_CALLBACK(on_take_clicked), g_strdup(id), free_closure_data, 0);
        gtk_box_pack_start(GTK_BOX(row), btn, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(app.items_box), row, FALSE, FALSE, 0);
    }
    gtk_widget_show_all(app.items_box);

    /* npcs with Talk / Attack / Quest buttons (role is not sent by LOOK,
     * so we offer all three and let the server's error codes tell the
     * player which action was appropriate). */
    clear_box(app.npcs_box);
    json_value_t *npcs = json_obj_get(root, "npcs");
    for (size_t i = 0; i < json_arr_len(npcs); i++) {
        const char *id = json_as_str(json_arr_get(npcs, i));
        if (!id) continue;
        GtkWidget *row = make_row(id);
        GtkWidget *talk = gtk_button_new_with_label("Talk");
        GtkWidget *attack = gtk_button_new_with_label("Attack");
        GtkWidget *quest = gtk_button_new_with_label("Quest");
        g_signal_connect_data(talk, "clicked", G_CALLBACK(on_talk_clicked), g_strdup(id), free_closure_data, 0);
        g_signal_connect_data(attack, "clicked", G_CALLBACK(on_attack_clicked), g_strdup(id), free_closure_data, 0);
        g_signal_connect_data(quest, "clicked", G_CALLBACK(on_quest_clicked), g_strdup(id), free_closure_data, 0);
        gtk_box_pack_start(GTK_BOX(row), talk, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(row), attack, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(row), quest, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(app.npcs_box), row, FALSE, FALSE, 0);
    }
    gtk_widget_show_all(app.npcs_box);
}

static void render_inventory_json(json_value_t *arr) {
    clear_box(app.inventory_box);
    for (size_t i = 0; i < json_arr_len(arr); i++) {
        const char *id = json_as_str(json_arr_get(arr, i));
        if (!id) continue;
        GtkWidget *row = make_row(id);
        GtkWidget *btn = gtk_button_new_with_label("Drop");
        g_signal_connect_data(btn, "clicked", G_CALLBACK(on_drop_clicked), g_strdup(id), free_closure_data, 0);
        gtk_box_pack_start(GTK_BOX(row), btn, FALSE, FALSE, 0);
        gtk_box_pack_start(GTK_BOX(app.inventory_box), row, FALSE, FALSE, 0);
    }
    gtk_widget_show_all(app.inventory_box);
}

static void render_status_json(json_value_t *obj) {
    double hp = json_as_num(json_obj_get(obj, "hp"), -1);
    double maxhp = json_as_num(json_obj_get(obj, "max_hp"), -1);
    const char *status = json_as_str(json_obj_get(obj, "status"));
    char buf[128];
    snprintf(buf, sizeof(buf), "HP: %.0f / %.0f  [%s]", hp, maxhp, status ? status : "?");
    gtk_label_set_text(GTK_LABEL(app.hp_label), buf);
}

static void render_who_json(json_value_t *obj) {
    json_value_t *room = json_obj_get(obj, "room");
    double server_n = json_as_num(json_obj_get(obj, "server"), 0);
    char buf[128];
    snprintf(buf, sizeof(buf), "Players in room: %zu   Server total: %.0f", json_arr_len(room), server_n);
    gtk_label_set_text(GTK_LABEL(app.counts_label), buf);
}

/* ---------------- protocol line handling ---------------- */

static void handle_evt(const char *line) {
    /* line starts right after "EVT " */
    char rest[1024];
    snprintf(rest, sizeof(rest), "%s", line);

    if (strncmp(rest, "ROOM PRESENCE ENTER ", 21) == 0) {
        log_append("* %s entered the room", rest + 21);
        send_line("LOOK"); /* keep the room view accurate */
    } else if (strncmp(rest, "ROOM PRESENCE LEAVE ", 21) == 0) {
        log_append("* %s left the room", rest + 21);
        send_line("LOOK");
    } else if (strncmp(rest, "ROOM CHAT ", 10) == 0) {
        char *sp = strchr(rest + 10, ' ');
        if (sp) { *sp = '\0'; chat_append(app.chat_room, "[room] %s: %s", rest + 10, sp + 1); }
    } else if (strncmp(rest, "GLOBAL CHAT ", 12) == 0) {
        char *sp = strchr(rest + 12, ' ');
        if (sp) { *sp = '\0'; chat_append(app.chat_global, "[global] %s: %s", rest + 12, sp + 1); }
    } else if (strncmp(rest, "GROUP CHAT ", 11) == 0) {
        char *sp = strchr(rest + 11, ' ');
        if (sp) { *sp = '\0'; chat_append(app.chat_group, "[group] %s: %s", rest + 11, sp + 1); }
    } else if (strncmp(rest, "GROUP INVITE ", 13) == 0) {
        chat_append(app.chat_group, "* %s invited you to their group (GROUP JOIN <id> to accept)", rest + 13);
    } else if (strncmp(rest, "GROUP JOIN ", 11) == 0) {
        chat_append(app.chat_group, "* %s joined the group", rest + 11);
    } else if (strncmp(rest, "GROUP LEAVE ", 12) == 0) {
        chat_append(app.chat_group, "* %s left the group", rest + 12);
    } else if (strncmp(rest, "STATS players=", 14) == 0) {
        log_append("* server now has %s player(s) online", rest + 14);
    } else {
        log_append("< EVT %s", rest);
    }
}

static void handle_response(const char *line) {
    char verb[32];
    if (!pending_pop(verb, sizeof(verb))) snprintf(verb, sizeof(verb), "?");

    log_append("< %s", line);

    int is_ok = strncmp(line, "OK", 2) == 0;
    if (!is_ok) return; /* ERR already logged; nothing else to update */

    const char *payload = line + 2;
    while (*payload == ' ') payload++;

    if (strcmp(verb, "CONNECT") == 0) {
        gtk_widget_set_sensitive(app.main_box, TRUE);
        send_line("LOOK");
    } else if (strcmp(verb, "LOOK") == 0) {
        json_value_t *v = json_parse(payload);
        if (v) { render_look_json(v); json_free(v); }
    } else if (strcmp(verb, "INVENTORY") == 0) {
        json_value_t *v = json_parse(payload);
        if (v) { render_inventory_json(v); json_free(v); }
    } else if (strcmp(verb, "STATUS") == 0) {
        json_value_t *v = json_parse(payload);
        if (v) { render_status_json(v); json_free(v); }
    } else if (strcmp(verb, "WHO") == 0) {
        json_value_t *v = json_parse(payload);
        if (v) { render_who_json(v); json_free(v); }
    } else if (strcmp(verb, "MOVE") == 0 || strcmp(verb, "TAKE") == 0 || strcmp(verb, "DROP") == 0) {
        /* refresh room + inventory so the GUI reflects the new state */
        send_line("LOOK");
        send_line("INVENTORY");
    } else if (strcmp(verb, "ATTACK") == 0 || strcmp(verb, "FLEE") == 0) {
        send_line("STATUS");
        json_value_t *v = json_parse(payload);
        if (v && json_as_str(json_obj_get(v, "status")) && strcmp(json_as_str(json_obj_get(v, "status")), "victory") == 0)
            send_line("LOOK");
        if (v) json_free(v);
    } else if (strcmp(verb, "QUEST") == 0) {
        json_value_t *v = json_parse(payload);
        if (v) {
            const char *qid = json_as_str(json_obj_get(v, "quest_id"));
            const char *status = json_as_str(json_obj_get(v, "status"));
            log_append("[quest] %s: %s", qid ? qid : "?", status ? status : "?");
            json_free(v);
        }
    }
}

static void process_line(char *line) {
    /* strip trailing \r if present */
    size_t n = strlen(line);
    if (n > 0 && line[n - 1] == '\r') line[n - 1] = '\0';
    if (!line[0]) return;

    if (strncmp(line, "EVT ", 4) == 0) handle_evt(line + 4);
    else if (strncmp(line, "OK", 2) == 0 || strncmp(line, "ERR", 3) == 0) handle_response(line);
    else log_append("< %s", line); /* initial "OK hello proto=1" greeting etc. */
}

static gboolean on_socket_data(GIOChannel *source, GIOCondition cond, gpointer data) {
    (void)source; (void)data;
    if (cond & (G_IO_HUP | G_IO_ERR)) {
        log_append("[disconnected from server]");
        app.fd = -1;
        return FALSE;
    }
    char chunk[NETBUF_SIZE];
    ssize_t n = recv(app.fd, chunk, sizeof(chunk) - 1, 0);
    if (n <= 0) {
        log_append("[disconnected from server]");
        app.fd = -1;
        return FALSE;
    }
    chunk[n] = '\0';
    if (app.netlen + (size_t)n >= sizeof(app.netbuf)) app.netlen = 0; /* defensive */
    memcpy(app.netbuf + app.netlen, chunk, (size_t)n + 1);
    app.netlen += (size_t)n;

    char *start = app.netbuf;
    char *nl;
    while ((nl = strchr(start, '\n')) != NULL) {
        *nl = '\0';
        process_line(start);
        start = nl + 1;
    }
    size_t remaining = strlen(start);
    memmove(app.netbuf, start, remaining + 1);
    app.netlen = remaining;
    return TRUE;
}

/* ---------------- top-level UI callbacks ---------------- */

static void on_connect_clicked(GtkButton *btn, gpointer data) {
    (void)btn; (void)data;
    const char *host = gtk_entry_get_text(GTK_ENTRY(app.host_entry));
    const char *port_s = gtk_entry_get_text(GTK_ENTRY(app.port_entry));
    const char *username = gtk_entry_get_text(GTK_ENTRY(app.username_entry));
    if (!username[0]) { log_append("[error] enter a username first"); return; }

    int port = atoi(port_s);
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, host, &addr.sin_addr) != 1) {
        log_append("[error] invalid host '%s' (use an IPv4 address)", host);
        close(fd);
        return;
    }
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        log_append("[error] connect failed: %s", strerror(errno));
        close(fd);
        return;
    }
    int one = 1;
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

    app.fd = fd;
    app.netlen = 0;
    pending_head = pending_tail = 0;
    app.chan = g_io_channel_unix_new(fd);
    app.watch_id = g_io_add_watch(app.chan, G_IO_IN | G_IO_HUP | G_IO_ERR, on_socket_data, NULL);

    log_append("[connecting to %s:%d as %s]", host, port, username);
    send_linef("CONNECT %s", username);
    gtk_widget_set_sensitive(app.connect_button, FALSE);
}

static void on_send_chat(GtkButton *btn, gpointer data) {
    (void)btn; (void)data;
    const char *msg = gtk_entry_get_text(GTK_ENTRY(app.chat_entry));
    if (!msg[0]) return;
    const char *scope = gtk_combo_box_text_get_active_text(GTK_COMBO_BOX_TEXT(app.scope_combo));
    send_linef("CHAT %s %s", scope ? scope : "GLOBAL", msg);
    gtk_entry_set_text(GTK_ENTRY(app.chat_entry), "");
}

static void on_look_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("LOOK"); }
static void on_status_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("STATUS"); }
static void on_who_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("WHO"); }
static void on_inventory_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("INVENTORY"); }
static void on_quests_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("QUESTS"); }
static void on_defend_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("DEFEND"); }
static void on_flee_clicked(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("FLEE"); }
static void on_quit_clicked(GtkButton *b, gpointer d) {
    (void)b; (void)d;
    send_line("QUIT");
    gtk_main_quit();
}
static void on_group_create(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("GROUP CREATE"); }
static void on_group_leave(GtkButton *b, gpointer d) { (void)b; (void)d; send_line("GROUP LEAVE"); }
static void on_group_invite(GtkButton *b, gpointer d) {
    (void)b; (void)d;
    const char *target = gtk_entry_get_text(GTK_ENTRY(app.group_target_entry));
    if (target[0]) send_linef("GROUP INVITE %s", target);
}
static void on_group_join(GtkButton *b, gpointer d) {
    (void)b; (void)d;
    const char *target = gtk_entry_get_text(GTK_ENTRY(app.group_target_entry));
    if (target[0]) send_linef("GROUP JOIN %s", target);
}

static gboolean on_window_delete(GtkWidget *w, GdkEvent *e, gpointer d) {
    (void)w; (void)e; (void)d;
    if (app.fd >= 0) send_line("QUIT");
    return FALSE;
}

/* ---------------- UI construction ---------------- */

static GtkWidget *labeled_list(const char *title, GtkWidget **out_box) {
    GtkWidget *frame = gtk_frame_new(title);
    GtkWidget *scroller = gtk_scrolled_window_new(NULL, NULL);
    gtk_scrolled_window_set_policy(GTK_SCROLLED_WINDOW(scroller), GTK_POLICY_NEVER, GTK_POLICY_AUTOMATIC);
    gtk_widget_set_size_request(scroller, -1, 110);
    GtkWidget *box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 2);
    gtk_container_add(GTK_CONTAINER(scroller), box);
    gtk_container_add(GTK_CONTAINER(frame), scroller);
    *out_box = box;
    return frame;
}

static GtkWidget *make_chat_tab(GtkTextBuffer **buf_out) {
    GtkWidget *scroller = gtk_scrolled_window_new(NULL, NULL);
    GtkWidget *view = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(view), FALSE);
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(view), GTK_WRAP_WORD_CHAR);
    *buf_out = gtk_text_view_get_buffer(GTK_TEXT_VIEW(view));
    gtk_container_add(GTK_CONTAINER(scroller), view);
    return scroller;
}

int main(int argc, char **argv) {
    gtk_init(&argc, &argv);
    memset(&app, 0, sizeof(app));
    app.fd = -1;

    app.window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(app.window), "TAP - A Shared-World Retro Text Adventure");
    gtk_window_set_default_size(GTK_WINDOW(app.window), 980, 700);
    g_signal_connect(app.window, "delete-event", G_CALLBACK(on_window_delete), NULL);
    g_signal_connect(app.window, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    GtkWidget *root = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_container_set_border_width(GTK_CONTAINER(root), 6);
    gtk_container_add(GTK_CONTAINER(app.window), root);

    /* --- connection bar --- */
    GtkWidget *connbar = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_box_pack_start(GTK_BOX(connbar), gtk_label_new("Host:"), FALSE, FALSE, 0);
    app.host_entry = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(app.host_entry), "127.0.0.1");
    gtk_entry_set_width_chars(GTK_ENTRY(app.host_entry), 12);
    gtk_box_pack_start(GTK_BOX(connbar), app.host_entry, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(connbar), gtk_label_new("Port:"), FALSE, FALSE, 0);
    app.port_entry = gtk_entry_new();
    gtk_entry_set_text(GTK_ENTRY(app.port_entry), "4242");
    gtk_entry_set_width_chars(GTK_ENTRY(app.port_entry), 6);
    gtk_box_pack_start(GTK_BOX(connbar), app.port_entry, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(connbar), gtk_label_new("Username:"), FALSE, FALSE, 0);
    app.username_entry = gtk_entry_new();
    gtk_box_pack_start(GTK_BOX(connbar), app.username_entry, FALSE, FALSE, 0);

    app.connect_button = gtk_button_new_with_label("Connect");
    g_signal_connect(app.connect_button, "clicked", G_CALLBACK(on_connect_clicked), NULL);
    gtk_box_pack_start(GTK_BOX(connbar), app.connect_button, FALSE, FALSE, 0);

    GtkWidget *quit_btn = gtk_button_new_with_label("Quit");
    g_signal_connect(quit_btn, "clicked", G_CALLBACK(on_quit_clicked), NULL);
    gtk_box_pack_end(GTK_BOX(connbar), quit_btn, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(root), connbar, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(root), gtk_separator_new(GTK_ORIENTATION_HORIZONTAL), FALSE, FALSE, 0);

    /* --- main area (disabled until connected) --- */
    app.main_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 6);
    gtk_widget_set_sensitive(app.main_box, FALSE);
    gtk_box_pack_start(GTK_BOX(root), app.main_box, TRUE, TRUE, 0);

    /* left column: room + world */
    GtkWidget *left = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);
    gtk_widget_set_size_request(left, 380, -1);

    app.room_name_label = gtk_label_new("Not connected");
    gtk_label_set_xalign(GTK_LABEL(app.room_name_label), 0.0);
    gtk_box_pack_start(GTK_BOX(left), app.room_name_label, FALSE, FALSE, 0);
    app.room_desc_label = gtk_label_new("");
    gtk_label_set_xalign(GTK_LABEL(app.room_desc_label), 0.0);
    gtk_label_set_line_wrap(GTK_LABEL(app.room_desc_label), TRUE);
    gtk_box_pack_start(GTK_BOX(left), app.room_desc_label, FALSE, FALSE, 0);

    app.exits_box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 4);
    gtk_box_pack_start(GTK_BOX(left), app.exits_box, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(left), labeled_list("Players here", &app.players_box), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(left), labeled_list("Items here", &app.items_box), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(left), labeled_list("NPCs here", &app.npcs_box), FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(left), labeled_list("Inventory", &app.inventory_box), FALSE, FALSE, 0);

    app.hp_label = gtk_label_new("HP: -- / --");
    gtk_label_set_xalign(GTK_LABEL(app.hp_label), 0.0);
    gtk_box_pack_start(GTK_BOX(left), app.hp_label, FALSE, FALSE, 0);
    app.counts_label = gtk_label_new("Players in room: -   Server total: -");
    gtk_label_set_xalign(GTK_LABEL(app.counts_label), 0.0);
    gtk_box_pack_start(GTK_BOX(left), app.counts_label, FALSE, FALSE, 0);

    /* action buttons */
    GtkWidget *actions = gtk_grid_new();
    gtk_grid_set_row_spacing(GTK_GRID(actions), 3);
    gtk_grid_set_column_spacing(GTK_GRID(actions), 3);
    struct { const char *label; GCallback cb; } action_defs[] = {
        {"Look", G_CALLBACK(on_look_clicked)}, {"Status", G_CALLBACK(on_status_clicked)},
        {"Inventory", G_CALLBACK(on_inventory_clicked)}, {"Who", G_CALLBACK(on_who_clicked)},
        {"Quests", G_CALLBACK(on_quests_clicked)}, {"Defend", G_CALLBACK(on_defend_clicked)},
        {"Flee", G_CALLBACK(on_flee_clicked)},
    };
    for (size_t i = 0; i < sizeof(action_defs) / sizeof(action_defs[0]); i++) {
        GtkWidget *b = gtk_button_new_with_label(action_defs[i].label);
        g_signal_connect(b, "clicked", action_defs[i].cb, NULL);
        gtk_grid_attach(GTK_GRID(actions), b, (int)(i % 4), (int)(i / 4), 1, 1);
    }
    gtk_box_pack_start(GTK_BOX(left), actions, FALSE, FALSE, 0);

    /* group controls */
    GtkWidget *group_frame = gtk_frame_new("Group");
    GtkWidget *group_box = gtk_box_new(GTK_ORIENTATION_VERTICAL, 3);
    gtk_container_add(GTK_CONTAINER(group_frame), group_box);
    GtkWidget *group_btns = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 3);
    GtkWidget *gcreate = gtk_button_new_with_label("Create");
    GtkWidget *gleave = gtk_button_new_with_label("Leave");
    g_signal_connect(gcreate, "clicked", G_CALLBACK(on_group_create), NULL);
    g_signal_connect(gleave, "clicked", G_CALLBACK(on_group_leave), NULL);
    gtk_box_pack_start(GTK_BOX(group_btns), gcreate, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(group_btns), gleave, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(group_box), group_btns, FALSE, FALSE, 0);

    app.group_target_entry = gtk_entry_new();
    gtk_entry_set_placeholder_text(GTK_ENTRY(app.group_target_entry), "username (invite) / group id (join)");
    gtk_box_pack_start(GTK_BOX(group_box), app.group_target_entry, FALSE, FALSE, 0);
    GtkWidget *group_btns2 = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 3);
    GtkWidget *ginvite = gtk_button_new_with_label("Invite");
    GtkWidget *gjoin = gtk_button_new_with_label("Join");
    g_signal_connect(ginvite, "clicked", G_CALLBACK(on_group_invite), NULL);
    g_signal_connect(gjoin, "clicked", G_CALLBACK(on_group_join), NULL);
    gtk_box_pack_start(GTK_BOX(group_btns2), ginvite, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(group_btns2), gjoin, TRUE, TRUE, 0);
    gtk_box_pack_start(GTK_BOX(group_box), group_btns2, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(left), group_frame, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(app.main_box), left, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(app.main_box), gtk_separator_new(GTK_ORIENTATION_VERTICAL), FALSE, FALSE, 0);

    /* right column: chat (tabs) over log */
    GtkWidget *right = gtk_box_new(GTK_ORIENTATION_VERTICAL, 4);

    GtkWidget *chat_frame = gtk_frame_new("Chat");
    GtkWidget *notebook = gtk_notebook_new();
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), make_chat_tab(&app.chat_global), gtk_label_new("Global"));
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), make_chat_tab(&app.chat_room), gtk_label_new("Room"));
    gtk_notebook_append_page(GTK_NOTEBOOK(notebook), make_chat_tab(&app.chat_group), gtk_label_new("Group"));
    gtk_container_add(GTK_CONTAINER(chat_frame), notebook);
    gtk_box_pack_start(GTK_BOX(right), chat_frame, TRUE, TRUE, 0);

    GtkWidget *chat_input_row = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 3);
    app.scope_combo = gtk_combo_box_text_new();
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(app.scope_combo), "GLOBAL");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(app.scope_combo), "ROOM");
    gtk_combo_box_text_append_text(GTK_COMBO_BOX_TEXT(app.scope_combo), "GROUP");
    gtk_combo_box_set_active(GTK_COMBO_BOX(app.scope_combo), 0);
    gtk_box_pack_start(GTK_BOX(chat_input_row), app.scope_combo, FALSE, FALSE, 0);
    app.chat_entry = gtk_entry_new();
    gtk_widget_set_hexpand(app.chat_entry, TRUE);
    g_signal_connect(app.chat_entry, "activate", G_CALLBACK(on_send_chat), NULL);
    gtk_box_pack_start(GTK_BOX(chat_input_row), app.chat_entry, TRUE, TRUE, 0);
    GtkWidget *send_btn = gtk_button_new_with_label("Send");
    g_signal_connect(send_btn, "clicked", G_CALLBACK(on_send_chat), NULL);
    gtk_box_pack_start(GTK_BOX(chat_input_row), send_btn, FALSE, FALSE, 0);
    gtk_box_pack_start(GTK_BOX(right), chat_input_row, FALSE, FALSE, 0);

    GtkWidget *log_frame = gtk_frame_new("Protocol Log");
    GtkWidget *log_scroller = gtk_scrolled_window_new(NULL, NULL);
    gtk_widget_set_size_request(log_scroller, -1, 220);
    app.log_view = gtk_text_view_new();
    gtk_text_view_set_editable(GTK_TEXT_VIEW(app.log_view), FALSE);
    gtk_text_view_set_wrap_mode(GTK_TEXT_VIEW(app.log_view), GTK_WRAP_WORD_CHAR);
    app.log_buffer = gtk_text_view_get_buffer(GTK_TEXT_VIEW(app.log_view));
    gtk_container_add(GTK_CONTAINER(log_scroller), app.log_view);
    gtk_container_add(GTK_CONTAINER(log_frame), log_scroller);
    gtk_box_pack_start(GTK_BOX(right), log_frame, FALSE, FALSE, 0);

    gtk_box_pack_start(GTK_BOX(app.main_box), right, TRUE, TRUE, 0);

    gtk_widget_show_all(app.window);
    log_append("Enter a username and click Connect to join the world.");

    gtk_main();

    if (app.fd >= 0) close(app.fd);
    return 0;
}
