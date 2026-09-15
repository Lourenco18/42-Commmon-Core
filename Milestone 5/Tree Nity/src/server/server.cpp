// server.cpp
//
// treenity message-queue server.
//
// Usage: ./server
// Prints the IPC identifier ("/tmp/operator.server.<pid>") to stdout on
// startup, then serves clients until SIGINT/SIGTERM.
//
// See README.md for the full protocol/architecture write-up. Short version:
//
//   * One FIFO ("the main endpoint") accepts line-based control requests:
//     CREATE, LIST, INFO, SUBSCRIBE, PRODUCE, DISCONNECT.
//   * Each request carries the path of a private response FIFO the client
//     already created, which the server opens just long enough to write
//     one reply line.
//   * SUBSCRIBE/PRODUCE additionally hand off to a per-session data FIFO
//     used for the actual message stream, read/written outside the control
//     protocol so producers never interleave and topics can push to many
//     consumers independently.
//   * Each topic owns one dedicated worker thread (topic.hpp) that is the
//     only writer to consumer FIFOs for that topic.

#include <atomic>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <mutex>
#include <poll.h>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <thread>
#include <unistd.h>
#include <unordered_map>

#include "../common/hashmap.hpp"
#include "../common/ipc_util.hpp"
#include "../common/protocol.hpp"
#include "topic.hpp"

using namespace treenity;

namespace {

// Persisted client metadata (subject VI.5). Deliberately uses the hand
// rolled HashMap, not std::unordered_map, because this is exactly the
// index the subject calls out as requiring a manual implementation.
struct ClientMeta {
    std::string client_id;
    std::string topic;
    uint32_t offset = 0;
    std::string prefix;
    std::string ipc; // this client's dedicated message-fifo path
};

HashMap<ClientMeta> g_client_index;

std::mutex g_topics_mu;
std::unordered_map<std::string, std::unique_ptr<Topic>> g_topics;

std::string g_ipc_id; // e.g. /tmp/operator.server.1337

std::atomic<bool> g_shutdown{false};

void on_signal(int) { g_shutdown.store(true); }

// --- response helpers ----------------------------------------------------

void reply(const std::string &resp_path, const std::string &line) {
    int fd = open(resp_path.c_str(), O_WRONLY);
    if (fd < 0) return; // client already gave up; nothing we can do
    write_all(fd, line + "\n");
    close(fd);
}

void reply_ok(const std::string &resp_path, const std::string &extra = "") {
    reply(resp_path, extra.empty() ? "OK" : "OK " + extra);
}

void reply_err(const std::string &resp_path, int code, const std::string &msg) {
    reply(resp_path, "ERR " + std::to_string(code) + " " + msg);
}

// --- request handlers ------------------------------------------------------

void handle_create(const std::vector<std::string> &f) {
    // CREATE <topic> <resp>
    if (f.size() != 3) return;
    const std::string &topic = f[1];
    const std::string &resp = f[2];
    if (!is_valid_identifier(topic)) {
        reply_err(resp, EXIT_GENERAL_ERROR, "invalid topic name");
        return;
    }
    std::lock_guard<std::mutex> lock(g_topics_mu);
    if (g_topics.count(topic)) {
        reply_err(resp, EXIT_TOPIC_ERROR, "topic already exists");
        return;
    }
    // The per-consumer offset-persist callback is a no-op here: consumer
    // offsets are actually persisted into g_client_index by handle_subscribe
    // rebinding it below is unnecessary because Topic calls back with just
    // (client_id, offset) -- persistence happens via g_client_index.set()
    // performed directly from that callback, defined at registration time
    // in handle_subscribe.
    auto t = std::make_unique<Topic>(topic, [topic](const std::string &client_id,
                                                      uint32_t offset) {
        ClientMeta meta;
        if (g_client_index.get(client_id, meta)) {
            meta.offset = offset;
            g_client_index.set(client_id, meta);
        }
    });
    g_topics[topic] = std::move(t);
    g_topics[topic]->start();
    reply_ok(resp);
}

void handle_list(const std::vector<std::string> &f) {
    // LIST <resp>
    if (f.size() != 2) return;
    const std::string &resp = f[1];
    std::string names;
    {
        std::lock_guard<std::mutex> lock(g_topics_mu);
        bool first = true;
        for (auto &kv : g_topics) {
            if (!first) names += ",";
            names += kv.first;
            first = false;
        }
    }
    reply_ok(resp, names);
}

void handle_info(const std::vector<std::string> &f) {
    // INFO <client_id> <resp>
    if (f.size() != 3) return;
    const std::string &client_id = f[1];
    const std::string &resp = f[2];
    ClientMeta meta;
    if (!g_client_index.get(client_id, meta)) {
        reply_err(resp, EXIT_TOPIC_ERROR, "client not found");
        return;
    }
    std::string json = "{\"client\":\"" + meta.client_id + "\",\"topic\":\"" + meta.topic +
                        "\",\"offset\":" + std::to_string(meta.offset) + ",\"prefix\":\"" +
                        meta.prefix + "\",\"ipc\":\"" + meta.ipc + "\"}";
    reply_ok(resp, json);
}

// Background thread: open the consumer's dedicated FIFO for writing (this
// blocks until the client opens its end for reading) then hand the fd to
// the topic so its worker can start delivering.
void consumer_opener_thread(Topic *topic, std::string client_id, std::string fifo_path) {
    int fd = open(fifo_path.c_str(), O_WRONLY);
    if (fd < 0) return;
    if (!topic->has_active_consumer(client_id)) {
        close(fd);
        return;
    }
    topic->attach_fd(client_id, fd);
}

void handle_subscribe(const std::vector<std::string> &f) {
    // SUBSCRIBE <topic> <client_id> <prefix|-> <offset|-1> <raw:0|1> <resp>
    if (f.size() != 7) return;
    const std::string &topic_name = f[1];
    const std::string &client_id = f[2];
    std::string prefix = f[3] == "-" ? "" : f[3];
    long long requested_offset = std::atoll(f[4].c_str());
    bool raw = f[5] == "1";
    const std::string &resp = f[6];

    if (!is_valid_identifier(client_id) || !is_valid_identifier(topic_name)) {
        reply_err(resp, EXIT_GENERAL_ERROR, "invalid identifier");
        return;
    }

    Topic *topic = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_topics_mu);
        auto it = g_topics.find(topic_name);
        if (it == g_topics.end()) {
            reply_err(resp, EXIT_TOPIC_ERROR, "topic not found");
            return;
        }
        topic = it->second.get();
    }

    if (topic->has_active_consumer(client_id)) {
        reply_err(resp, EXIT_TOPIC_ERROR, "duplicate client name");
        return;
    }

    uint32_t start_offset = 0;
    ClientMeta meta;
    bool had_meta = g_client_index.get(client_id, meta);
    if (requested_offset >= 0) {
        start_offset = static_cast<uint32_t>(requested_offset);
    } else if (had_meta && meta.topic == topic_name) {
        start_offset = meta.offset; // resume
    } else {
        start_offset = 0; // brand new consumer
    }

    std::string fifo_path = g_ipc_id + "." + client_id;
    fifo_create(fifo_path);

    meta.client_id = client_id;
    meta.topic = topic_name;
    meta.offset = start_offset;
    meta.prefix = prefix;
    meta.ipc = fifo_path;
    g_client_index.set(client_id, meta);

    topic->register_consumer(client_id, prefix, start_offset, raw);

    reply_ok(resp);

    std::thread(consumer_opener_thread, topic, client_id, fifo_path).detach();
}

void producer_reader_thread(Topic *topic, std::string fifo_path, bool raw) {
    int fd = open(fifo_path.c_str(), O_RDONLY);
    if (fd < 0) {
        fifo_remove(fifo_path);
        return;
    }
    if (!raw) {
        std::string line;
        while (read_line(fd, line)) {
            auto pos = line.find(':');
            if (pos == std::string::npos) continue; // malformed line, ignore
            std::string key = line.substr(0, pos);
            std::string value = line.substr(pos + 1);
            if (key.size() + value.size() <= MAX_KEY_BODY_BYTES) {
                topic->produce(key, value);
            }
        }
    } else {
        for (;;) {
            char hdr[4];
            if (!read_all(fd, hdr, 4)) break;
            uint32_t keysize;
            read_u32le(hdr, keysize);
            std::string key(keysize, '\0');
            if (keysize > 0 && !read_all(fd, &key[0], keysize)) break;
            if (!read_all(fd, hdr, 4)) break;
            uint32_t valsize;
            read_u32le(hdr, valsize);
            std::string value(valsize, '\0');
            if (valsize > 0 && !read_all(fd, &value[0], valsize)) break;
            if (key.size() + value.size() <= MAX_KEY_BODY_BYTES) {
                topic->produce(key, value);
            }
        }
    }
    close(fd);
    fifo_remove(fifo_path);
}

void handle_produce(const std::vector<std::string> &f) {
    // PRODUCE <topic> <raw:0|1> <producer_fifo> <resp>
    if (f.size() != 5) return;
    const std::string &topic_name = f[1];
    bool raw = f[2] == "1";
    const std::string &fifo_path = f[3];
    const std::string &resp = f[4];

    Topic *topic = nullptr;
    {
        std::lock_guard<std::mutex> lock(g_topics_mu);
        auto it = g_topics.find(topic_name);
        if (it == g_topics.end()) {
            reply_err(resp, EXIT_TOPIC_ERROR, "topic not found");
            return;
        }
        topic = it->second.get();
    }
    reply_ok(resp);
    std::thread(producer_reader_thread, topic, fifo_path, raw).detach();
}

void handle_disconnect(const std::vector<std::string> &f) {
    // DISCONNECT <client_id>
    if (f.size() != 2) return;
    const std::string &client_id = f[1];
    ClientMeta meta;
    if (!g_client_index.get(client_id, meta)) return;
    std::lock_guard<std::mutex> lock(g_topics_mu);
    auto it = g_topics.find(meta.topic);
    if (it != g_topics.end()) it->second->unregister_consumer(client_id);
}

void dispatch(const std::string &line) {
    if (line.empty()) return;
    std::vector<std::string> f = split(line, ' ');
    const std::string &cmd = f[0];
    if (cmd == "CREATE") handle_create(f);
    else if (cmd == "LIST") handle_list(f);
    else if (cmd == "INFO") handle_info(f);
    else if (cmd == "SUBSCRIBE") handle_subscribe(f);
    else if (cmd == "PRODUCE") handle_produce(f);
    else if (cmd == "DISCONNECT") handle_disconnect(f);
    // unknown commands are ignored (defensive: a stray/malformed line must
    // never crash the server)
}

} // namespace

int main() {
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);
    signal(SIGPIPE, SIG_IGN); // a dead consumer must not kill the server

    pid_t pid = getpid();
    g_ipc_id = std::string("/tmp/") + IPC_NAME_PREFIX + ".server." + std::to_string(pid);

    if (!fifo_create(g_ipc_id)) {
        fprintf(stderr, "server: failed to create main fifo %s: %s\n", g_ipc_id.c_str(),
                strerror(errno));
        return EXIT_GENERAL_ERROR;
    }

    // Open O_RDWR so the fifo always has at least one writer (ourselves):
    // read() then blocks for new lines instead of returning EOF whenever
    // the last real client closes.
    int main_fd = open(g_ipc_id.c_str(), O_RDWR | O_NONBLOCK);
    if (main_fd < 0) {
        fprintf(stderr, "server: failed to open main fifo: %s\n", strerror(errno));
        fifo_remove(g_ipc_id);
        return EXIT_GENERAL_ERROR;
    }

    printf("%s\n", g_ipc_id.c_str());
    fflush(stdout);

    std::string pending;
    char buf[4096];
    while (!g_shutdown.load()) {
        struct pollfd pfd;
        pfd.fd = main_fd;
        pfd.events = POLLIN;
        int rc = poll(&pfd, 1, 150);
        if (rc < 0) {
            if (errno == EINTR) continue;
            break;
        }
        if (rc == 0) continue; // timeout, re-check shutdown flag
        ssize_t n = read(main_fd, buf, sizeof(buf));
        if (n <= 0) continue; // spurious (no real writer) or transient
        pending.append(buf, static_cast<size_t>(n));
        size_t nl;
        while ((nl = pending.find('\n')) != std::string::npos) {
            std::string line = pending.substr(0, nl);
            pending.erase(0, nl + 1);
            dispatch(line);
        }
    }

    // Graceful shutdown, with a hard 5s watchdog per the subject.
    std::thread watchdog([] {
        std::this_thread::sleep_for(std::chrono::seconds(GRACEFUL_SHUTDOWN_TIMEOUT_SEC));
        _exit(EXIT_OK);
    });
    watchdog.detach();

    {
        std::lock_guard<std::mutex> lock(g_topics_mu);
        for (auto &kv : g_topics) kv.second->stop(); // flushes backlog + sentinels
        g_topics.clear();
    }

    close(main_fd);
    fifo_remove(g_ipc_id);
    return EXIT_OK;
}
