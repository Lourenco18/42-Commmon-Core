/* jsonmin.h - Minimal, dependency-free JSON writer + parser used by the
 * TAP server and clients. Kept intentionally small: we only need to
 * build/read the flat-ish JSON structures defined by RFC 42TAP. */
#ifndef TAP_JSONMIN_H
#define TAP_JSONMIN_H

#include <stddef.h>

/* ---------- Growable string buffer (JSON writer) ---------- */
typedef struct {
    char *data;
    size_t len;
    size_t cap;
} sbuf_t;

void sb_init(sbuf_t *sb);
void sb_free(sbuf_t *sb);
void sb_append(sbuf_t *sb, const char *s);
void sb_appendf(sbuf_t *sb, const char *fmt, ...);
/* Appends `s` as a JSON string literal, including quotes and escaping. */
void sb_append_json_string(sbuf_t *sb, const char *s);

/* ---------- Minimal JSON value tree (JSON parser) ---------- */
typedef enum {
    JV_NULL, JV_BOOL, JV_NUM, JV_STR, JV_ARR, JV_OBJ
} json_type_t;

typedef struct json_value {
    json_type_t type;
    union {
        int boolean;
        double number;
        char *string;
        struct { struct json_value **items; size_t count; } arr;
        struct { char **keys; struct json_value **vals; size_t count; } obj;
    } u;
} json_value_t;

/* Parses a JSON document. Returns NULL on parse error. Caller must
 * call json_free() on the result. */
json_value_t *json_parse(const char *text);
void json_free(json_value_t *v);

/* Accessors. Return NULL / defaults if not applicable. */
json_value_t *json_obj_get(const json_value_t *obj, const char *key);
size_t json_arr_len(const json_value_t *arr);
json_value_t *json_arr_get(const json_value_t *arr, size_t idx);
const char *json_as_str(const json_value_t *v); /* NULL if not string */
double json_as_num(const json_value_t *v, double def);

#endif
