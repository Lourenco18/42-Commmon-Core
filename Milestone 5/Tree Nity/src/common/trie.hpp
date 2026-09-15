// trie.hpp
//
// Prefix tree (trie) indexing *consumers* by the key-prefix they subscribed
// with (subject section VI.9 / VI.10: "Topic handlers maintain an efficient
// data structure of consumers indexed by prefix").
//
// Each node represents one character of a registered prefix. A node may
// carry zero or more consumer ids (several consumers can share the same
// prefix). Given an incoming message key, `match()` walks the trie one
// character at a time following the key, and collects every consumer id
// found on the path -- exactly the consumers whose prefix is a prefix of
// the key.
//
// The empty prefix ("") is handled separately (see PrefixIndex below) as a
// flat list, per the subject: "Direct Addition: Empty-prefix consumers are
// added directly to the delivery list without data structure traversal."

#pragma once

#include <algorithm>
#include <string>
#include <unordered_map>
#include <vector>

namespace treenity {

class PrefixTrie {
public:
    PrefixTrie() : root_(new Node()) {}
    ~PrefixTrie() { destroy(root_); }

    PrefixTrie(const PrefixTrie &) = delete;
    PrefixTrie &operator=(const PrefixTrie &) = delete;

    // Registers `consumer_id` under `prefix`. `prefix` must be non-empty;
    // empty-prefix consumers belong in PrefixIndex's direct list instead.
    void insert(const std::string &prefix, const std::string &consumer_id) {
        Node *node = root_;
        for (char c : prefix) {
            node = node->child(c, /*create=*/true);
        }
        if (std::find(node->consumers.begin(), node->consumers.end(), consumer_id) ==
            node->consumers.end()) {
            node->consumers.push_back(consumer_id);
        }
    }

    // Removes `consumer_id` from `prefix`. No-op if not present.
    void remove(const std::string &prefix, const std::string &consumer_id) {
        Node *node = root_;
        for (char c : prefix) {
            node = node->child(c, /*create=*/false);
            if (!node) return;
        }
        auto &v = node->consumers;
        v.erase(std::remove(v.begin(), v.end(), consumer_id), v.end());
    }

    // Returns every consumer id registered under a prefix that is a prefix
    // of `key` (exact match on the prefix counts too, e.g. prefix "user"
    // matches key "user" and key "user.login", but not "admin").
    std::vector<std::string> match(const std::string &key) const {
        std::vector<std::string> result;
        Node *node = root_;
        for (const auto &id : node->consumers) result.push_back(id);
        for (char c : key) {
            node = node->child(c, /*create=*/false);
            if (!node) break;
            for (const auto &id : node->consumers) result.push_back(id);
        }
        return result;
    }

    bool empty() const { return root_->children.empty() && root_->consumers.empty(); }

private:
    struct Node {
        std::unordered_map<char, Node *> children;
        std::vector<std::string> consumers;

        Node *child(char c, bool create) {
            auto it = children.find(c);
            if (it != children.end()) return it->second;
            if (!create) return nullptr;
            Node *n = new Node();
            children[c] = n;
            return n;
        }
    };

    static void destroy(Node *n) {
        if (!n) return;
        for (auto &kv : n->children) destroy(kv.second);
        delete n;
    }

    Node *root_;
};

// Convenience free function used both by the trie's own logic and by the
// server's catch-up/replay path, so the "what counts as a match" rule lives
// in exactly one place.
inline bool prefix_matches(const std::string &prefix, const std::string &key) {
    if (prefix.empty()) return true; // wildcard
    if (prefix.size() > key.size()) return false;
    return key.compare(0, prefix.size(), prefix) == 0;
}

// Wraps a PrefixTrie plus the empty-prefix fast path into the full index
// described by the subject.
class PrefixIndex {
public:
    void add(const std::string &prefix, const std::string &consumer_id) {
        if (prefix.empty()) {
            if (std::find(wildcard_.begin(), wildcard_.end(), consumer_id) == wildcard_.end())
                wildcard_.push_back(consumer_id);
        } else {
            trie_.insert(prefix, consumer_id);
        }
    }

    void remove(const std::string &prefix, const std::string &consumer_id) {
        if (prefix.empty()) {
            wildcard_.erase(std::remove(wildcard_.begin(), wildcard_.end(), consumer_id),
                             wildcard_.end());
        } else {
            trie_.remove(prefix, consumer_id);
        }
    }

    std::vector<std::string> match(const std::string &key) const {
        std::vector<std::string> result = wildcard_;
        for (auto &id : trie_.match(key)) result.push_back(id);
        return result;
    }

private:
    PrefixTrie trie_;
    std::vector<std::string> wildcard_;
};

} // namespace treenity
