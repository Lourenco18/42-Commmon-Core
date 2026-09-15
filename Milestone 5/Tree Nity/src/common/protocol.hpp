// protocol.hpp
//
// Shared constants and wire-format helpers for the treenity message queue.
//
// IPC transport: named pipes (FIFOs). See README.md "IPC Choice" for the
// justification. Two kinds of channel are used:
//
//   1. The server's *main* FIFO ("/tmp/<name>.server.<pid>"): a line-based
//      control channel. Every line is one atomic control request (creating
//      a topic, listing topics, registering a producer/consumer, querying
//      metadata). Requests always carry the path of a private one-shot
//      "response FIFO" that the client created beforehand, so the server
//      can answer even though a FIFO is one-way.
//
//   2. Per-session data FIFOs, created by the client, used for the actual
//      message stream: one for a producer's outgoing messages, one for a
//      subscribed consumer's incoming messages. These are long-lived for
//      the duration of the command and are read/written directly (no
//      control-line framing needed) which keeps concurrent producers from
//      interleaving on a shared channel.
//
// Control lines are plain space-separated ASCII fields. Every identifier
// allowed by the subject ("^[a-zA-Z0-9_.-]{1,32}$") never contains spaces,
// so this simple split is unambiguous and every line comfortably fits
// inside PIPE_BUF (4096 bytes on Linux), which the kernel guarantees to
// write atomically -- so concurrent clients writing to the shared main
// FIFO never see interleaved/corrupted requests.

#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace treenity {

constexpr size_t MAX_KEY_BODY_BYTES = 1024; // key+value, excludes framing metadata
constexpr int GRACEFUL_SHUTDOWN_TIMEOUT_SEC = 5;
constexpr const char *IPC_NAME_PREFIX = "operator";

// Exit codes (subject VIII.4), in descending precedence order.
enum ExitCode {
    EXIT_OK = 0,
    EXIT_GENERAL_ERROR = 1,   // bad args, invalid ipc identifier, connection failure
    EXIT_TOPIC_ERROR = 2,     // topic/client errors
    EXIT_IPC_ERROR = 3,       // ipc communication error / server disconnection
};

// Raw binary sentinel used to wake a blocked consumer on graceful shutdown:
// offset == UINT32_MAX with zero-length key/value. Never produced by a real
// message because offsets are assigned sequentially starting at 0.
constexpr uint32_t SENTINEL_OFFSET = 0xFFFFFFFFu;
// Text-mode equivalent: a single ASCII "End Of Transmission" byte on its
// own line.
constexpr char SENTINEL_TEXT_LINE = '\x04';

inline std::vector<std::string> split(const std::string &s, char sep = ' ') {
    std::vector<std::string> out;
    std::string cur;
    for (char c : s) {
        if (c == sep) {
            out.push_back(cur);
            cur.clear();
        } else {
            cur.push_back(c);
        }
    }
    out.push_back(cur);
    return out;
}

inline bool is_valid_identifier(const std::string &s) {
    if (s.empty() || s.size() > 32) return false;
    for (char c : s) {
        bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
                  (c >= '0' && c <= '9') || c == '_' || c == '.' || c == '-';
        if (!ok) return false;
    }
    return true;
}

// --- little-endian 32-bit helpers for --raw mode -----------------------

inline void write_u32le(std::string &out, uint32_t v) {
    out.push_back(static_cast<char>(v & 0xFF));
    out.push_back(static_cast<char>((v >> 8) & 0xFF));
    out.push_back(static_cast<char>((v >> 16) & 0xFF));
    out.push_back(static_cast<char>((v >> 24) & 0xFF));
}

inline bool read_u32le(const char *buf, uint32_t &v) {
    v = (static_cast<uint8_t>(buf[0])) | (static_cast<uint8_t>(buf[1]) << 8) |
        (static_cast<uint8_t>(buf[2]) << 16) | (static_cast<uint8_t>(buf[3]) << 24);
    return true;
}

struct Message {
    uint32_t offset = 0;
    std::string key;
    std::string value;
};

} // namespace treenity
