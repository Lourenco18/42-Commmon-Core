// hashmap.hpp
//
// A minimal string-keyed hashmap with explicit collision resolution by
// separate chaining (each bucket is a singly linked list of entries).
//
// This is used for the mandatory "client metadata" index described in the
// subject (section VI.5): the subject explicitly forbids using the standard
// library's hashmap/dictionary types (std::unordered_map, std::map, ...)
// for this specific piece of state, so it is hand rolled here.
//
// It is intentionally small and single purpose (string -> ClientMetadata)
// rather than a fully generic container, to keep the collision-resolution
// logic easy to read and easy to unit test.

#pragma once

#include <cstddef>
#include <functional>
#include <mutex>
#include <string>
#include <vector>

namespace treenity {

// djb2 string hash - simple, fast, and good enough distribution for the
// small (<32 char) client/topic identifiers used in this project.
inline unsigned long djb2_hash(const std::string &s) {
    unsigned long hash = 5381;
    for (unsigned char c : s) {
        hash = ((hash << 5) + hash) + c; // hash * 33 + c
    }
    return hash;
}

// Thread-safe string -> Value hashmap with separate chaining.
template <typename Value>
class HashMap {
public:
    explicit HashMap(size_t bucket_count = 64) : buckets_(bucket_count) {}

    // Insert or overwrite the value for `key`. Returns true if this created
    // a brand new entry, false if it overwrote an existing one.
    bool set(const std::string &key, const Value &value) {
        std::lock_guard<std::mutex> lock(mutex_);
        Bucket &bucket = bucket_for(key);
        for (auto &entry : bucket) {
            if (entry.key == key) {
                entry.value = value;
                return false;
            }
        }
        bucket.push_back(Entry{key, value});
        size_++;
        maybe_rehash();
        return true;
    }

    // Returns true and fills `out` if the key exists.
    bool get(const std::string &key, Value &out) const {
        std::lock_guard<std::mutex> lock(mutex_);
        const Bucket &bucket = bucket_for(key);
        for (const auto &entry : bucket) {
            if (entry.key == key) {
                out = entry.value;
                return true;
            }
        }
        return false;
    }

    bool contains(const std::string &key) const {
        std::lock_guard<std::mutex> lock(mutex_);
        const Bucket &bucket = bucket_for(key);
        for (const auto &entry : bucket) {
            if (entry.key == key) return true;
        }
        return false;
    }

    bool remove(const std::string &key) {
        std::lock_guard<std::mutex> lock(mutex_);
        Bucket &bucket = bucket_for(key);
        for (auto it = bucket.begin(); it != bucket.end(); ++it) {
            if (it->key == key) {
                bucket.erase(it);
                size_--;
                return true;
            }
        }
        return false;
    }

    // Runs `fn(key, value)` for every stored entry. Used sparingly (e.g. to
    // list topics); not on the hot message-delivery path.
    template <typename Fn>
    void for_each(Fn fn) const {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto &bucket : buckets_) {
            for (const auto &entry : bucket) {
                fn(entry.key, entry.value);
            }
        }
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return size_;
    }

    size_t bucket_count() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return buckets_.size();
    }

private:
    struct Entry {
        std::string key;
        Value value;
    };
    using Bucket = std::vector<Entry>;

    Bucket &bucket_for(const std::string &key) {
        return buckets_[djb2_hash(key) % buckets_.size()];
    }
    const Bucket &bucket_for(const std::string &key) const {
        return buckets_[djb2_hash(key) % buckets_.size()];
    }

    // Grows the table (doubling) once the load factor passes 0.75, and
    // re-distributes every entry into the new bucket array. Keeps average
    // chain length short as the client count grows.
    void maybe_rehash() {
        if (static_cast<double>(size_) / buckets_.size() <= 0.75) return;
        std::vector<Bucket> new_buckets(buckets_.size() * 2);
        for (auto &bucket : buckets_) {
            for (auto &entry : bucket) {
                auto &nb = new_buckets[djb2_hash(entry.key) % new_buckets.size()];
                nb.push_back(std::move(entry));
            }
        }
        buckets_ = std::move(new_buckets);
    }

    mutable std::mutex mutex_;
    std::vector<Bucket> buckets_;
    size_t size_ = 0;
};

} // namespace treenity
