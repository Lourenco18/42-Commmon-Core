#include "log.h"
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <time.h>

static FILE *g_logfile = NULL;

void log_init(const char *logfile) {
    if (logfile) {
        g_logfile = fopen(logfile, "a");
        if (!g_logfile) {
            fprintf(stderr, "warning: could not open log file %s, logging to stdout only\n", logfile);
        }
    }
}

void log_close(void) {
    if (g_logfile) { fclose(g_logfile); g_logfile = NULL; }
}

static const char *level_str(log_level_t level) {
    switch (level) {
        case LOG_INFO: return "INFO";
        case LOG_WARN: return "WARN";
        case LOG_ERROR: return "ERROR";
    }
    return "INFO";
}

static void write_line(FILE *out, const char *ts, const char *event, log_level_t level, const char *fields_fmt, va_list ap) {
    char fields[1024];
    vsnprintf(fields, sizeof(fields), fields_fmt ? fields_fmt : "", ap);
    if (fields[0] != '\0') {
        fprintf(out, "{\"ts\":\"%s\",\"level\":\"%s\",\"event\":\"%s\",%s}\n", ts, level_str(level), event, fields);
    } else {
        fprintf(out, "{\"ts\":\"%s\",\"level\":\"%s\",\"event\":\"%s\"}\n", ts, level_str(level), event);
    }
    fflush(out);
}

void log_line(log_level_t level, const char *event, const char *fields_fmt, ...) {
    time_t now = time(NULL);
    struct tm tmv;
    gmtime_r(&now, &tmv);
    char ts[32];
    strftime(ts, sizeof(ts), "%Y-%m-%dT%H:%M:%SZ", &tmv);

    va_list ap;
    va_start(ap, fields_fmt);
    write_line(stdout, ts, event, level, fields_fmt, ap);
    va_end(ap);

    if (g_logfile) {
        va_start(ap, fields_fmt);
        write_line(g_logfile, ts, event, level, fields_fmt, ap);
        va_end(ap);
    }
}
