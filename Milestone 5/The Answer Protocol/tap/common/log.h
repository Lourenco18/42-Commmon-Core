/* log.h - structured JSON logging shared by the server.
 * Each call writes one JSON line to stdout and to the log file, e.g.:
 *   {"ts":"2026-09-02T12:00:00Z","level":"INFO","event":"connect","ip":"127.0.0.1","player":"alice"}
 */
#ifndef TAP_LOG_H
#define TAP_LOG_H

#include <stdio.h>

typedef enum { LOG_INFO, LOG_WARN, LOG_ERROR } log_level_t;

/* Must be called once at startup. logfile may be NULL to log to stdout only. */
void log_init(const char *logfile);
void log_close(void);

/* fields is a printf-style fragment of additional JSON key/value pairs,
 * WITHOUT a leading comma, e.g. log_line(LOG_INFO,"connect","\"ip\":\"%s\"",ip); */
void log_line(log_level_t level, const char *event, const char *fields_fmt, ...);

#endif
