// client.cpp
//
// treenity message-queue client. A single executable providing every
// subcommand described in the subject (VIII.1): create, list, produce,
// subscribe, info.
//
//   ./client <ipc_identifier> create <topic_name>
//   ./client <ipc_identifier> list
//   ./client <ipc_identifier> produce <topic_name> [--raw]
//   ./client <ipc_identifier> subscribe <topic> <name> [--prefix P] [--offset N] [--raw]
//   ./client <ipc_identifier> info <client_id>

#include <atomic>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <sys/types.h>
#include <unistd.h>
#include <vector>

#include "../common/ipc_util.hpp"
#include "../common/protocol.hpp"

using namespace treenity;

namespace {

std::atomic<bool> g_signaled{false};
void on_signal(int) { g_signaled.store(true); }

// Signal-aware variants used only by the subscribe loop: unlike
// ipc_util.hpp's read_all()/read_line() (which deliberately retry on
// EINTR so ordinary I/O elsewhere in the client is robust to spurious
// interrupts), these must NOT retry -- SIGINT/SIGTERM install a handler
// with no SA_RESTART specifically so a blocked read() here returns EINTR,
// and the subscribe loop needs to see that and check g_signaled instead of
// silently going back to sleep in the kernel.
bool read_all_interruptible(int fd, char *data, size_t len) {
    size_t got = 0;
    while (got < len) {
        ssize_t n = read(fd, data + got, len - got);
        if (n < 0) {
            if (errno == EINTR) return false;
            return false;
        }
        if (n == 0) return false;
        got += static_cast<size_t>(n);
    }
    return true;
}

bool read_line_interruptible(int fd, std::string &out) {
    out.clear();
    char c;
    bool any = false;
    for (;;) {
        ssize_t n = read(fd, &c, 1);
        if (n < 0) {
            if (errno == EINTR) return false;
            return any;
        }
        if (n == 0) return any;
        any = true;
        if (c == '\n') return true;
        out.push_back(c);
    }
}

std::string make_tmp_path(const std::string &tag) {
    return "/tmp/." + std::string(IPC_NAME_PREFIX) + "." + tag + "." + std::to_string(getpid()) +
           "." + std::to_string(rand());
}

[[noreturn]] void die(int code, const std::string &msg) {
    fprintf(stderr, "client: %s\n", msg.c_str());
    exit(code);
}

// Sends `line` to the server's main fifo. Returns false (and the caller
// should exit(1)) if the ipc identifier does not correspond to a live
// server.
bool send_request(const std::string &ipc_id, const std::string &line) {
    int fd = open(ipc_id.c_str(), O_WRONLY);
    if (fd < 0) return false;
    bool ok = write_all(fd, line + "\n");
    close(fd);
    return ok;
}

// Sends a request that expects exactly one reply line on a fresh private
// response fifo. Returns false if the server never answers (treated as a
// disconnection by the caller).
bool request_reply(const std::string &ipc_id, const std::string &cmd_without_resp,
                    std::string &reply_line) {
    std::string resp_path = make_tmp_path("resp");
    if (!fifo_create(resp_path)) die(EXIT_IPC_ERROR, "failed to create response channel");

    if (!send_request(ipc_id, cmd_without_resp + " " + resp_path)) {
        fifo_remove(resp_path);
        die(EXIT_GENERAL_ERROR, "invalid ipc identifier");
    }

    int fd = open(resp_path.c_str(), O_RDONLY);
    if (fd < 0) {
        fifo_remove(resp_path);
        return false;
    }
    bool ok = read_line(fd, reply_line);
    close(fd);
    fifo_remove(resp_path);
    return ok;
}

// Parses "OK ..." / "ERR <code> <msg>" and exits the process accordingly
// when it's an error. Returns the text after "OK " (possibly empty) on
// success.
std::string expect_ok_or_die(const std::string &reply_line) {
    if (reply_line.rfind("OK", 0) == 0) {
        return reply_line.size() > 3 ? reply_line.substr(3) : "";
    }
    if (reply_line.rfind("ERR", 0) == 0) {
        auto parts = split(reply_line, ' ');
        int code = parts.size() > 1 ? std::atoi(parts[1].c_str()) : EXIT_GENERAL_ERROR;
        std::string msg;
        for (size_t i = 2; i < parts.size(); ++i) {
            if (i > 2) msg += " ";
            msg += parts[i];
        }
        die(code, msg.empty() ? "request failed" : msg);
    }
    die(EXIT_IPC_ERROR, "malformed server response");
}

std::string find_opt(std::vector<std::string> &args, const std::string &name, bool takes_value) {
    for (size_t i = 0; i < args.size(); ++i) {
        if (args[i] == name) {
            std::string value;
            if (takes_value && i + 1 < args.size()) {
                value = args[i + 1];
                args.erase(args.begin() + i, args.begin() + i + 2);
            } else {
                args.erase(args.begin() + i);
                value = "1";
            }
            return value;
        }
    }
    return "";
}

// --- subcommands -----------------------------------------------------------

int cmd_create(const std::string &ipc_id, std::vector<std::string> &args) {
    if (args.size() != 1) die(EXIT_GENERAL_ERROR, "usage: create <topic_name>");
    const std::string &topic = args[0];
    if (!is_valid_identifier(topic)) die(EXIT_GENERAL_ERROR, "invalid topic name");
    std::string reply;
    if (!request_reply(ipc_id, "CREATE " + topic, reply)) die(EXIT_IPC_ERROR, "server disconnected");
    expect_ok_or_die(reply);
    printf("topic created\n");
    return EXIT_OK;
}

int cmd_list(const std::string &ipc_id, std::vector<std::string> &args) {
    (void)args;
    std::string reply;
    if (!request_reply(ipc_id, "LIST", reply)) die(EXIT_IPC_ERROR, "server disconnected");
    std::string names = expect_ok_or_die(reply);
    if (!names.empty() && names[0] == ' ') names.erase(0, 1);
    printf("%s\n", names.c_str());
    return EXIT_OK;
}

int cmd_info(const std::string &ipc_id, std::vector<std::string> &args) {
    if (args.size() != 1) die(EXIT_GENERAL_ERROR, "usage: info <client_id>");
    std::string reply;
    if (!request_reply(ipc_id, "INFO " + args[0], reply)) die(EXIT_IPC_ERROR, "server disconnected");
    std::string json = expect_ok_or_die(reply);
    if (!json.empty() && json[0] == ' ') json.erase(0, 1);
    printf("%s\n", json.c_str());
    return EXIT_OK;
}

int cmd_produce(const std::string &ipc_id, std::vector<std::string> &args) {
    bool raw = !find_opt(args, "--raw", false).empty();
    if (args.size() != 1) die(EXIT_GENERAL_ERROR, "usage: produce <topic> [--raw]");
    const std::string &topic = args[0];
    if (!is_valid_identifier(topic)) die(EXIT_GENERAL_ERROR, "invalid topic name");

    std::string producer_fifo = make_tmp_path("producer");
    if (!fifo_create(producer_fifo)) die(EXIT_IPC_ERROR, "failed to create producer channel");

    std::string reply;
    std::string cmd = std::string("PRODUCE ") + topic + " " + (raw ? "1" : "0") + " " +
                       producer_fifo;
    if (!request_reply(ipc_id, cmd, reply)) {
        fifo_remove(producer_fifo);
        die(EXIT_IPC_ERROR, "server disconnected");
    }
    expect_ok_or_die(reply);

    int fd = open(producer_fifo.c_str(), O_WRONLY);
    if (fd < 0) {
        fifo_remove(producer_fifo);
        die(EXIT_IPC_ERROR, "failed to open producer channel");
    }

    if (!raw) {
        std::string line;
        while (std::getline(std::cin, line)) {
            auto pos = line.find(':');
            if (pos == std::string::npos) {
                fprintf(stderr, "client: malformed input line, expected key:body\n");
                continue;
            }
            std::string key = line.substr(0, pos);
            std::string value = line.substr(pos + 1);
            if (key.size() + value.size() > MAX_KEY_BODY_BYTES) {
                fprintf(stderr, "client: message exceeds %zu byte limit, skipped\n",
                        MAX_KEY_BODY_BYTES);
                continue;
            }
            write_all(fd, line + "\n");
        }
    } else {
        for (;;) {
            char hdr[4];
            ssize_t n = fread(hdr, 1, 4, stdin);
            if (n == 0) break; // clean EOF at record boundary
            if (n != 4) die(EXIT_GENERAL_ERROR, "truncated record at EOF");
            uint32_t keysize;
            read_u32le(hdr, keysize);
            std::string key(keysize, '\0');
            if (keysize > 0 && fread(&key[0], 1, keysize, stdin) != keysize)
                die(EXIT_GENERAL_ERROR, "truncated record at EOF");
            if (fread(hdr, 1, 4, stdin) != 4) die(EXIT_GENERAL_ERROR, "truncated record at EOF");
            uint32_t valsize;
            read_u32le(hdr, valsize);
            std::string value(valsize, '\0');
            if (valsize > 0 && fread(&value[0], 1, valsize, stdin) != valsize)
                die(EXIT_GENERAL_ERROR, "truncated record at EOF");
            if (key.size() + value.size() > MAX_KEY_BODY_BYTES) {
                fprintf(stderr, "client: message exceeds %zu byte limit, skipped\n",
                        MAX_KEY_BODY_BYTES);
                continue;
            }
            std::string wire;
            write_u32le(wire, keysize);
            wire += key;
            write_u32le(wire, valsize);
            wire += value;
            write_all(fd, wire);
        }
    }
    close(fd);
    fifo_remove(producer_fifo);
    return EXIT_OK;
}

int cmd_subscribe(const std::string &ipc_id, std::vector<std::string> &args) {
    std::string prefix = find_opt(args, "--prefix", true);
    std::string offset_str = find_opt(args, "--offset", true);
    bool raw = !find_opt(args, "--raw", false).empty();
    if (args.size() != 2)
        die(EXIT_GENERAL_ERROR, "usage: subscribe <topic> <name> [--prefix P] [--offset N] [--raw]");
    const std::string &topic = args[0];
    const std::string &client_id = args[1];
    if (!is_valid_identifier(topic) || !is_valid_identifier(client_id))
        die(EXIT_GENERAL_ERROR, "invalid topic or client identifier");

    long long offset = offset_str.empty() ? -1 : std::atoll(offset_str.c_str());
    std::string cmd = "SUBSCRIBE " + topic + " " + client_id + " " +
                       (prefix.empty() ? "-" : prefix) + " " + std::to_string(offset) + " " +
                       (raw ? "1" : "0");
    std::string reply;
    if (!request_reply(ipc_id, cmd, reply)) die(EXIT_IPC_ERROR, "server disconnected");
    expect_ok_or_die(reply);

    printf("subscribed to %s\n", topic.c_str());
    fflush(stdout);

    std::string msg_fifo = ipc_id + "." + client_id;
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_signal;
    sa.sa_flags = 0; // deliberately no SA_RESTART: blocking read() must return EINTR
    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);

    int fd = open(msg_fifo.c_str(), O_RDONLY);
    if (fd < 0) die(EXIT_IPC_ERROR, "failed to open message channel");

    bool disconnected_locally = false;
    if (!raw) {
        std::string line;
        while (true) {
            if (g_signaled.load()) { disconnected_locally = true; break; }
            if (!read_line_interruptible(fd, line)) {
                if (g_signaled.load()) disconnected_locally = true;
                break; // server closed, or interrupted -> shutdown
            }
            if (line.size() == 1 && line[0] == SENTINEL_TEXT_LINE) break;
            printf("%s\n", line.c_str());
            fflush(stdout);
        }
    } else {
        for (;;) {
            if (g_signaled.load()) { disconnected_locally = true; break; }
            char hdr[4];
            if (!read_all_interruptible(fd, hdr, 4)) {
                if (g_signaled.load()) disconnected_locally = true;
                break;
            }
            uint32_t offset_field;
            read_u32le(hdr, offset_field);
            char sz[4];
            if (!read_all_interruptible(fd, sz, 4)) {
                if (g_signaled.load()) disconnected_locally = true;
                break;
            }
            uint32_t keysize;
            read_u32le(sz, keysize);
            if (offset_field == SENTINEL_OFFSET && keysize == 0) break; // sentinel
            std::string key(keysize, '\0');
            if (keysize > 0 && !read_all_interruptible(fd, &key[0], keysize)) break;
            if (!read_all_interruptible(fd, sz, 4)) break;
            uint32_t valsize;
            read_u32le(sz, valsize);
            std::string value(valsize, '\0');
            if (valsize > 0 && !read_all_interruptible(fd, &value[0], valsize)) break;

            std::string wire;
            write_u32le(wire, offset_field);
            write_u32le(wire, keysize);
            wire += key;
            write_u32le(wire, valsize);
            wire += value;
            fwrite(wire.data(), 1, wire.size(), stdout);
            fflush(stdout);
        }
    }
    close(fd);

    if (disconnected_locally) {
        // Best-effort: tell the server so it frees this consumer's slot
        // immediately instead of waiting to notice a broken pipe.
        send_request(ipc_id, "DISCONNECT " + client_id);
    }
    return EXIT_OK;
}

} // namespace

int main(int argc, char **argv) {
    srand(static_cast<unsigned>(getpid()) ^ static_cast<unsigned>(time(nullptr)));

    if (argc < 3) {
        fprintf(stderr,
                "usage: %s <ipc_identifier> <create|list|produce|subscribe|info> [...]\n",
                argv[0]);
        return EXIT_GENERAL_ERROR;
    }

    std::string ipc_id = argv[1];
    std::string subcmd = argv[2];
    std::vector<std::string> args;
    for (int i = 3; i < argc; ++i) args.push_back(argv[i]);

    if (subcmd == "create") return cmd_create(ipc_id, args);
    if (subcmd == "list") return cmd_list(ipc_id, args);
    if (subcmd == "produce") return cmd_produce(ipc_id, args);
    if (subcmd == "subscribe") return cmd_subscribe(ipc_id, args);
    if (subcmd == "info") return cmd_info(ipc_id, args);

    fprintf(stderr, "client: unknown subcommand '%s'\n", subcmd.c_str());
    return EXIT_GENERAL_ERROR;
}
