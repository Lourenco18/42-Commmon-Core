// topic.hpp
//
// A Topic owns its message log and a dedicated worker thread (subject
// VI.7: "Thread/Routine per Topic: At least one dedicated thread or
// routine must be assigned per topic for message processing").
//
// The worker thread is the single place that ever writes to a consumer's
// dedicated FIFO for that topic, which keeps the delivery logic simple:
// no extra locking is needed around the write itself, only around the
// shared log/consumer state that producer threads and the control thread
// also touch.

#pragma once

#include <atomic>
#include <condition_variable>
#include <cstring>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include "../common/ipc_util.hpp"
#include "../common/protocol.hpp"
#include "../common/trie.hpp"

namespace treenity {

// Called by the topic worker whenever it advances a consumer's committed
// offset, so the server's persisted client-metadata hashmap stays in sync
// (used to answer `info` and to resume a later subscribe).
using OffsetPersistCb = std::function<void(const std::string &client_id, uint32_t offset)>;

class Topic {
public:
    struct ConsumerState {
        std::string id;
        std::string prefix;
        uint32_t offset = 0;
        bool raw = false;
        int fd = -1;
        bool connected = false; // fd is open and ready to receive
        bool wanted = true;     // false once unregistered / disconnecting
    };

    Topic(std::string name, OffsetPersistCb persist_cb)
        : name_(std::move(name)), persist_cb_(std::move(persist_cb)) {}

    ~Topic() { stop(); }

    void start() {
        worker_ = std::thread([this] { run(); });
    }

    // Signals the worker to flush pending backlog, wake every connected
    // consumer with a sentinel, then exit. Joins the thread (bounded by
    // the worker's own short poll interval, so this returns quickly).
    void stop() {
        if (!worker_.joinable()) return;
        shutting_down_.store(true);
        cv_.notify_all();
        worker_.join();
    }

    // Appends a message to the log and wakes the worker. Returns the
    // assigned offset.
    uint32_t produce(const std::string &key, const std::string &value) {
        std::lock_guard<std::mutex> lock(mu_);
        uint32_t offset = static_cast<uint32_t>(log_.size());
        log_.push_back(Message{offset, key, value});
        cv_.notify_all();
        return offset;
    }

    // Registers (or re-registers, on resume) a consumer starting at
    // `start_offset`. The FIFO node at `fd_path` must already exist; this
    // function does not block -- the caller is expected to open it for
    // writing on a background thread and call attach_fd() once ready.
    void register_consumer(const std::string &id, const std::string &prefix,
                            uint32_t start_offset, bool raw) {
        std::lock_guard<std::mutex> lock(mu_);
        ConsumerState st;
        st.id = id;
        st.prefix = prefix;
        st.offset = start_offset;
        st.raw = raw;
        st.connected = false;
        st.wanted = true;
        consumers_[id] = st;
        if (!prefix.empty()) prefix_index_.add(prefix, id);
        cv_.notify_all();
    }

    // Called from the background "open for write" thread once the FIFO
    // rendezvous with the client has completed.
    void attach_fd(const std::string &id, int fd) {
        std::lock_guard<std::mutex> lock(mu_);
        auto it = consumers_.find(id);
        if (it == consumers_.end() || !it->second.wanted) {
            close(fd);
            return;
        }
        it->second.fd = fd;
        it->second.connected = true;
        cv_.notify_all();
    }

    bool has_active_consumer(const std::string &id) const {
        std::lock_guard<std::mutex> lock(mu_);
        auto it = consumers_.find(id);
        return it != consumers_.end() && it->second.wanted;
    }

    void unregister_consumer(const std::string &id) {
        std::lock_guard<std::mutex> lock(mu_);
        auto it = consumers_.find(id);
        if (it == consumers_.end()) return;
        if (!it->second.prefix.empty()) prefix_index_.remove(it->second.prefix, id);
        if (it->second.fd >= 0) close(it->second.fd);
        consumers_.erase(it);
    }

    const std::string &name() const { return name_; }

private:
    bool has_pending_work_locked() const {
        for (auto &kv : consumers_) {
            if (kv.second.connected && kv.second.offset < log_.size()) return true;
        }
        return false;
    }

    static std::string encode_text(const Message &m) { return m.key + ":" + m.value + "\n"; }

    static std::string encode_raw(const Message &m) {
        std::string out;
        write_u32le(out, m.offset);
        write_u32le(out, static_cast<uint32_t>(m.key.size()));
        out += m.key;
        write_u32le(out, static_cast<uint32_t>(m.value.size()));
        out += m.value;
        return out;
    }

    static std::string encode_sentinel(bool raw) {
        if (raw) {
            std::string out;
            write_u32le(out, SENTINEL_OFFSET);
            write_u32le(out, 0);
            write_u32le(out, 0);
            return out;
        }
        return std::string(1, SENTINEL_TEXT_LINE) + "\n";
    }

    void run() {
        std::unique_lock<std::mutex> lock(mu_);
        while (true) {
            cv_.wait_for(lock, std::chrono::milliseconds(150), [this] {
                return shutting_down_.load() || has_pending_work_locked();
            });
            if (shutting_down_.load()) break;

            for (auto &kv : consumers_) {
                ConsumerState &c = kv.second;
                if (!c.connected) continue;
                while (c.offset < log_.size()) {
                    const Message &m = log_[c.offset];
                    bool match = prefix_matches(c.prefix, m.key);
                    if (match) {
                        std::string wire = c.raw ? encode_raw(m) : encode_text(m);
                        if (!write_all(c.fd, wire)) {
                            c.connected = false;
                            close(c.fd);
                            c.fd = -1;
                            break;
                        }
                    }
                    c.offset++;
                    if (persist_cb_) persist_cb_(c.id, c.offset);
                }
            }
        }

        // Shutdown: wake every still-connected consumer with a sentinel so
        // its blocking read() returns and it can exit(0) instead of hanging.
        for (auto &kv : consumers_) {
            ConsumerState &c = kv.second;
            if (c.connected && c.fd >= 0) {
                std::string sentinel = encode_sentinel(c.raw);
                write_all(c.fd, sentinel);
                close(c.fd);
                c.fd = -1;
                c.connected = false;
            }
        }
    }

    std::string name_;
    OffsetPersistCb persist_cb_;

    mutable std::mutex mu_;
    std::condition_variable cv_;
    std::vector<Message> log_;
    std::unordered_map<std::string, ConsumerState> consumers_;
    PrefixIndex prefix_index_;

    std::atomic<bool> shutting_down_{false};
    std::thread worker_;
};

} // namespace treenity
