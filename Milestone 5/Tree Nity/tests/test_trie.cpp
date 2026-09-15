// test_trie.cpp
//
// Unit tests for the prefix-matching data structure (subject VI.11: "The
// prefix matching functionality requires comprehensive unit testing").
// Covers: exact/partial/no-match, empty-prefix wildcard behaviour, shared
// prefixes across multiple consumers, removal, and larger-scale sanity.

#include <algorithm>
#include <gtest/gtest.h>

#include "../src/common/trie.hpp"

using treenity::PrefixIndex;
using treenity::PrefixTrie;
using treenity::prefix_matches;

namespace {

std::vector<std::string> sorted(std::vector<std::string> v) {
    std::sort(v.begin(), v.end());
    return v;
}

} // namespace

// --- prefix_matches() free function -----------------------------------

TEST(PrefixMatches, ExactMatch) {
    EXPECT_TRUE(prefix_matches("user", "user"));
}

TEST(PrefixMatches, PartialMatch) {
    EXPECT_TRUE(prefix_matches("user", "user.login"));
}

TEST(PrefixMatches, NoMatch) {
    EXPECT_FALSE(prefix_matches("user", "admin"));
}

TEST(PrefixMatches, EmptyPrefixMatchesEverything) {
    EXPECT_TRUE(prefix_matches("", "anything"));
    EXPECT_TRUE(prefix_matches("", ""));
}

TEST(PrefixMatches, PrefixLongerThanKeyNeverMatches) {
    EXPECT_FALSE(prefix_matches("user.login", "user"));
}

TEST(PrefixMatches, CaseSensitive) {
    EXPECT_FALSE(prefix_matches("User", "user.login"));
}

// --- PrefixTrie ----------------------------------------------------------

TEST(PrefixTrie, BasicInsertAndMatch) {
    PrefixTrie t;
    t.insert("user", "c1");
    EXPECT_EQ(sorted(t.match("user")), sorted({"c1"}));
    EXPECT_EQ(sorted(t.match("user.login")), sorted({"c1"}));
    EXPECT_TRUE(t.match("admin").empty());
}

TEST(PrefixTrie, MultipleConsumersSharePrefix) {
    PrefixTrie t;
    t.insert("user", "c1");
    t.insert("user", "c2");
    EXPECT_EQ(sorted(t.match("user.create")), sorted({"c1", "c2"}));
}

TEST(PrefixTrie, NestedPrefixesAllMatchAlongThePath) {
    PrefixTrie t;
    t.insert("user", "broad");
    t.insert("user.create", "narrow");
    // "user.create.extra" starts with both "user" and "user.create"
    EXPECT_EQ(sorted(t.match("user.create.extra")), sorted({"broad", "narrow"}));
    // "user.update" only starts with "user"
    EXPECT_EQ(sorted(t.match("user.update")), sorted({"broad"}));
}

TEST(PrefixTrie, RemoveStopsFutureMatches) {
    PrefixTrie t;
    t.insert("orders", "c1");
    t.insert("orders", "c2");
    t.remove("orders", "c1");
    EXPECT_EQ(sorted(t.match("orders.new")), sorted({"c2"}));
}

TEST(PrefixTrie, RemoveUnknownConsumerIsNoop) {
    PrefixTrie t;
    t.insert("orders", "c1");
    t.remove("orders", "does-not-exist");
    EXPECT_EQ(sorted(t.match("orders")), sorted({"c1"}));
}

TEST(PrefixTrie, EmptyTrieMatchesNothing) {
    PrefixTrie t;
    EXPECT_TRUE(t.match("anything").empty());
    EXPECT_TRUE(t.empty());
}

TEST(PrefixTrie, LargeScaleManyPrefixesAndKeys) {
    PrefixTrie t;
    // Zero-padded to a fixed width so no prefix is accidentally a prefix of
    // another (e.g. unpadded "topic1" would also match "topic10.event").
    char buf[16];
    for (int i = 0; i < 500; ++i) {
        snprintf(buf, sizeof(buf), "topic%04d", i);
        t.insert(buf, "consumer" + std::to_string(i));
    }
    for (int i = 0; i < 500; ++i) {
        snprintf(buf, sizeof(buf), "topic%04d", i);
        auto m = t.match(std::string(buf) + ".event");
        ASSERT_EQ(m.size(), 1u);
        EXPECT_EQ(m[0], "consumer" + std::to_string(i));
    }
    EXPECT_TRUE(t.match("unrelated_key").empty());
}

// --- PrefixIndex (trie + empty-prefix fast path) --------------------------

TEST(PrefixIndex, EmptyPrefixConsumerMatchesEverything) {
    PrefixIndex idx;
    idx.add("", "wildcard");
    idx.add("user", "specific");
    EXPECT_EQ(sorted(idx.match("anything")), sorted({"wildcard"}));
    EXPECT_EQ(sorted(idx.match("user.create")), sorted({"wildcard", "specific"}));
}

TEST(PrefixIndex, RemoveEmptyPrefixConsumer) {
    PrefixIndex idx;
    idx.add("", "wildcard");
    idx.remove("", "wildcard");
    EXPECT_TRUE(idx.match("anything").empty());
}

TEST(PrefixIndex, MixedPrefixAndWildcardConsumers) {
    PrefixIndex idx;
    idx.add("", "all");
    idx.add("user.create", "creators");
    idx.add("user.delete", "deleters");
    EXPECT_EQ(sorted(idx.match("user.create")), sorted({"all", "creators"}));
    EXPECT_EQ(sorted(idx.match("user.delete")), sorted({"all", "deleters"}));
    EXPECT_EQ(sorted(idx.match("order.new")), sorted({"all"}));
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
