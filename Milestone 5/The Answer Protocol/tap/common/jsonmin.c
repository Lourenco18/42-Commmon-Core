/* jsonmin.c - see jsonmin.h */
#include "jsonmin.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <ctype.h>

/* ================= Writer ================= */

void sb_init(sbuf_t *sb) {
    sb->cap = 256;
    sb->len = 0;
    sb->data = malloc(sb->cap);
    sb->data[0] = '\0';
}

void sb_free(sbuf_t *sb) {
    free(sb->data);
    sb->data = NULL;
    sb->len = sb->cap = 0;
}

static void sb_ensure(sbuf_t *sb, size_t extra) {
    if (sb->len + extra + 1 > sb->cap) {
        while (sb->len + extra + 1 > sb->cap) sb->cap *= 2;
        sb->data = realloc(sb->data, sb->cap);
    }
}

void sb_append(sbuf_t *sb, const char *s) {
    size_t l = strlen(s);
    sb_ensure(sb, l);
    memcpy(sb->data + sb->len, s, l + 1);
    sb->len += l;
}

void sb_appendf(sbuf_t *sb, const char *fmt, ...) {
    char stackbuf[512];
    va_list ap;
    va_start(ap, fmt);
    int needed = vsnprintf(stackbuf, sizeof(stackbuf), fmt, ap);
    va_end(ap);
    if (needed < 0) return;
    if ((size_t)needed < sizeof(stackbuf)) {
        sb_append(sb, stackbuf);
        return;
    }
    char *heapbuf = malloc((size_t)needed + 1);
    va_start(ap, fmt);
    vsnprintf(heapbuf, (size_t)needed + 1, fmt, ap);
    va_end(ap);
    sb_append(sb, heapbuf);
    free(heapbuf);
}

void sb_append_json_string(sbuf_t *sb, const char *s) {
    sb_ensure(sb, strlen(s) * 2 + 2);
    sb->data[sb->len++] = '"';
    for (const unsigned char *p = (const unsigned char *)s; *p; p++) {
        sb_ensure(sb, 8);
        switch (*p) {
            case '"':  sb->data[sb->len++] = '\\'; sb->data[sb->len++] = '"'; break;
            case '\\': sb->data[sb->len++] = '\\'; sb->data[sb->len++] = '\\'; break;
            case '\n': sb->data[sb->len++] = '\\'; sb->data[sb->len++] = 'n'; break;
            case '\r': sb->data[sb->len++] = '\\'; sb->data[sb->len++] = 'r'; break;
            case '\t': sb->data[sb->len++] = '\\'; sb->data[sb->len++] = 't'; break;
            default:
                if (*p < 0x20) {
                    int n = snprintf(sb->data + sb->len, 8, "\\u%04x", *p);
                    sb->len += (size_t)n;
                } else {
                    sb->data[sb->len++] = (char)*p;
                }
        }
    }
    sb_ensure(sb, 2);
    sb->data[sb->len++] = '"';
    sb->data[sb->len] = '\0';
}

/* ================= Parser ================= */

typedef struct { const char *p; } parser_t;

static void skip_ws(parser_t *ps) {
    while (*ps->p && isspace((unsigned char)*ps->p)) ps->p++;
}

static json_value_t *jv_new(json_type_t t) {
    json_value_t *v = calloc(1, sizeof(json_value_t));
    v->type = t;
    return v;
}

static json_value_t *parse_value(parser_t *ps);

static char *parse_raw_string(parser_t *ps) {
    if (*ps->p != '"') return NULL;
    ps->p++;
    size_t cap = 32, len = 0;
    char *out = malloc(cap);
    while (*ps->p && *ps->p != '"') {
        char c = *ps->p++;
        if (c == '\\' && *ps->p) {
            char e = *ps->p++;
            switch (e) {
                case 'n': c = '\n'; break;
                case 't': c = '\t'; break;
                case 'r': c = '\r'; break;
                case '"': c = '"'; break;
                case '\\': c = '\\'; break;
                case '/': c = '/'; break;
                case 'u': {
                    /* skip 4 hex digits, emit '?' as a naive fallback */
                    for (int i = 0; i < 4 && *ps->p; i++) ps->p++;
                    c = '?';
                    break;
                }
                default: c = e;
            }
        }
        if (len + 1 >= cap) { cap *= 2; out = realloc(out, cap); }
        out[len++] = c;
    }
    if (*ps->p == '"') ps->p++;
    out[len] = '\0';
    return out;
}

static json_value_t *parse_string(parser_t *ps) {
    char *s = parse_raw_string(ps);
    if (!s) return NULL;
    json_value_t *v = jv_new(JV_STR);
    v->u.string = s;
    return v;
}

static json_value_t *parse_number(parser_t *ps) {
    const char *start = ps->p;
    if (*ps->p == '-') ps->p++;
    while (isdigit((unsigned char)*ps->p)) ps->p++;
    if (*ps->p == '.') { ps->p++; while (isdigit((unsigned char)*ps->p)) ps->p++; }
    if (*ps->p == 'e' || *ps->p == 'E') {
        ps->p++;
        if (*ps->p == '+' || *ps->p == '-') ps->p++;
        while (isdigit((unsigned char)*ps->p)) ps->p++;
    }
    json_value_t *v = jv_new(JV_NUM);
    v->u.number = strtod(start, NULL);
    return v;
}

static json_value_t *parse_array(parser_t *ps) {
    ps->p++; /* [ */
    json_value_t *v = jv_new(JV_ARR);
    size_t cap = 4;
    v->u.arr.items = malloc(cap * sizeof(json_value_t *));
    v->u.arr.count = 0;
    skip_ws(ps);
    if (*ps->p == ']') { ps->p++; return v; }
    while (1) {
        skip_ws(ps);
        json_value_t *item = parse_value(ps);
        if (!item) break;
        if (v->u.arr.count >= cap) { cap *= 2; v->u.arr.items = realloc(v->u.arr.items, cap * sizeof(json_value_t *)); }
        v->u.arr.items[v->u.arr.count++] = item;
        skip_ws(ps);
        if (*ps->p == ',') { ps->p++; continue; }
        if (*ps->p == ']') { ps->p++; break; }
        break;
    }
    return v;
}

static json_value_t *parse_object(parser_t *ps) {
    ps->p++; /* { */
    json_value_t *v = jv_new(JV_OBJ);
    size_t cap = 4;
    v->u.obj.keys = malloc(cap * sizeof(char *));
    v->u.obj.vals = malloc(cap * sizeof(json_value_t *));
    v->u.obj.count = 0;
    skip_ws(ps);
    if (*ps->p == '}') { ps->p++; return v; }
    while (1) {
        skip_ws(ps);
        char *key = parse_raw_string(ps);
        if (!key) break;
        skip_ws(ps);
        if (*ps->p == ':') ps->p++;
        skip_ws(ps);
        json_value_t *val = parse_value(ps);
        if (v->u.obj.count >= cap) {
            cap *= 2;
            v->u.obj.keys = realloc(v->u.obj.keys, cap * sizeof(char *));
            v->u.obj.vals = realloc(v->u.obj.vals, cap * sizeof(json_value_t *));
        }
        v->u.obj.keys[v->u.obj.count] = key;
        v->u.obj.vals[v->u.obj.count] = val;
        v->u.obj.count++;
        skip_ws(ps);
        if (*ps->p == ',') { ps->p++; continue; }
        if (*ps->p == '}') { ps->p++; break; }
        break;
    }
    return v;
}

static json_value_t *parse_value(parser_t *ps) {
    skip_ws(ps);
    switch (*ps->p) {
        case '"': return parse_string(ps);
        case '{': return parse_object(ps);
        case '[': return parse_array(ps);
        case 't':
            if (strncmp(ps->p, "true", 4) == 0) { ps->p += 4; json_value_t *v = jv_new(JV_BOOL); v->u.boolean = 1; return v; }
            return NULL;
        case 'f':
            if (strncmp(ps->p, "false", 5) == 0) { ps->p += 5; json_value_t *v = jv_new(JV_BOOL); v->u.boolean = 0; return v; }
            return NULL;
        case 'n':
            if (strncmp(ps->p, "null", 4) == 0) { ps->p += 4; return jv_new(JV_NULL); }
            return NULL;
        default:
            if (*ps->p == '-' || isdigit((unsigned char)*ps->p)) return parse_number(ps);
            return NULL;
    }
}

json_value_t *json_parse(const char *text) {
    parser_t ps = { text };
    skip_ws(&ps);
    return parse_value(&ps);
}

void json_free(json_value_t *v) {
    if (!v) return;
    switch (v->type) {
        case JV_STR: free(v->u.string); break;
        case JV_ARR:
            for (size_t i = 0; i < v->u.arr.count; i++) json_free(v->u.arr.items[i]);
            free(v->u.arr.items);
            break;
        case JV_OBJ:
            for (size_t i = 0; i < v->u.obj.count; i++) { free(v->u.obj.keys[i]); json_free(v->u.obj.vals[i]); }
            free(v->u.obj.keys);
            free(v->u.obj.vals);
            break;
        default: break;
    }
    free(v);
}

json_value_t *json_obj_get(const json_value_t *obj, const char *key) {
    if (!obj || obj->type != JV_OBJ) return NULL;
    for (size_t i = 0; i < obj->u.obj.count; i++)
        if (strcmp(obj->u.obj.keys[i], key) == 0) return obj->u.obj.vals[i];
    return NULL;
}

size_t json_arr_len(const json_value_t *arr) {
    if (!arr || arr->type != JV_ARR) return 0;
    return arr->u.arr.count;
}

json_value_t *json_arr_get(const json_value_t *arr, size_t idx) {
    if (!arr || arr->type != JV_ARR || idx >= arr->u.arr.count) return NULL;
    return arr->u.arr.items[idx];
}

const char *json_as_str(const json_value_t *v) {
    if (!v || v->type != JV_STR) return NULL;
    return v->u.string;
}

double json_as_num(const json_value_t *v, double def) {
    if (!v || v->type != JV_NUM) return def;
    return v->u.number;
}
