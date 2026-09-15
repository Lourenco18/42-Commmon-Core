// ipc_util.hpp
//
// Small wrappers around POSIX named-pipe (FIFO) calls: create, open,
// full read/write, and cleanup. Kept separate from protocol.hpp so the
// wire-format code stays free of syscalls (and is easy to unit test).

#pragma once

#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <string>
#include <sys/stat.h>
#include <unistd.h>

namespace treenity {

inline bool fifo_create(const std::string &path) {
    unlink(path.c_str()); // best effort: clear any stale node first
    if (mkfifo(path.c_str(), 0600) != 0 && errno != EEXIST) {
        return false;
    }
    return true;
}

inline void fifo_remove(const std::string &path) { unlink(path.c_str()); }

// Writes the whole buffer, retrying on partial writes / EINTR.
inline bool write_all(int fd, const char *data, size_t len) {
    size_t written = 0;
    while (written < len) {
        ssize_t n = write(fd, data + written, len - written);
        if (n < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        written += static_cast<size_t>(n);
    }
    return true;
}

inline bool write_all(int fd, const std::string &data) {
    return write_all(fd, data.data(), data.size());
}

// Reads exactly `len` bytes, retrying on partial reads / EINTR.
// Returns false on EOF-before-len or a real read error.
inline bool read_all(int fd, char *data, size_t len) {
    size_t got = 0;
    while (got < len) {
        ssize_t n = read(fd, data + got, len - got);
        if (n < 0) {
            if (errno == EINTR) continue;
            return false;
        }
        if (n == 0) return false; // EOF
        got += static_cast<size_t>(n);
    }
    return true;
}

// Reads a single '\n'-terminated line (without the newline). Returns false
// on EOF with nothing read.
inline bool read_line(int fd, std::string &out) {
    out.clear();
    char c;
    bool any = false;
    for (;;) {
        ssize_t n = read(fd, &c, 1);
        if (n < 0) {
            if (errno == EINTR) continue;
            return any;
        }
        if (n == 0) return any; // EOF
        any = true;
        if (c == '\n') return true;
        out.push_back(c);
    }
}

} // namespace treenity
