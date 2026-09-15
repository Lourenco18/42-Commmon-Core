// test_hashmap.cpp
//
// Unit tests for the manually implemented, chaining-based hashmap used for
// client metadata indexing (subject VI.5: "standard library hashmap/
// dictionary types are not allowed for this part").

#include <gtest/gtest.h>
#include <string>
#include <thread>
#include <vector>

#include "../src/common/hashmap.hpp"

using treenity::HashMap;

TEST(HashMap, SetAndGet) {
    HashMap<int> m;
    EXPECT_TRUE(m.set("a", 1));
    int out = 0;
    EXPECT_TRUE(m.get("a", out));
    EXPECT_EQ(out, 1);
}

TEST(HashMap, GetMissingKeyReturnsFalse) {
    HashMap<int> m;
    int out = 0;
    EXPECT_FALSE(m.get("missing", out));
}

TEST(HashMap, SetOverwritesExistingKey) {
    HashMap<int> m;
    EXPECT_TRUE(m.set("a", 1));   // new entry
    EXPECT_FALSE(m.set("a", 2));  // overwrite, not new
    int out = 0;
    m.get("a", out);
    EXPECT_EQ(out, 2);
    EXPECT_EQ(m.size(), 1u);
}

TEST(HashMap, Remove) {
    HashMap<int> m;
    m.set("a", 1);
    EXPECT_TRUE(m.remove("a"));
    EXPECT_FALSE(m.contains("a"));
    EXPECT_FALSE(m.remove("a")); // already gone
}

TEST(HashMap, CollisionResolutionKeepsAllEntriesRetrievable) {
    // Force every key into the same bucket (bucket_count = 1): every
    // insert collides, exercising the chaining resolution directly.
    HashMap<int> m(1);
    for (int i = 0; i < 50; ++i) {
        m.set("key" + std::to_string(i), i);
    }
    EXPECT_EQ(m.size(), 50u);
    for (int i = 0; i < 50; ++i) {
        int out = -1;
        ASSERT_TRUE(m.get("key" + std::to_string(i), out)) << i;
        EXPECT_EQ(out, i);
    }
}

TEST(HashMap, RehashPreservesAllEntries) {
    // Starts small so growth (rehashing) is exercised well before 1000
    // entries are inserted.
    HashMap<int> m(4);
    for (int i = 0; i < 1000; ++i) m.set("k" + std::to_string(i), i * 2);
    EXPECT_GT(m.bucket_count(), 4u);
    for (int i = 0; i < 1000; ++i) {
        int out = -1;
        ASSERT_TRUE(m.get("k" + std::to_string(i), out));
        EXPECT_EQ(out, i * 2);
    }
}

TEST(HashMap, ForEachVisitsEveryEntryExactlyOnce) {
    HashMap<int> m;
    for (int i = 0; i < 20; ++i) m.set("k" + std::to_string(i), i);
    std::vector<int> seen;
    m.for_each([&](const std::string &, int v) { seen.push_back(v); });
    EXPECT_EQ(seen.size(), 20u);
}

TEST(HashMap, ConcurrentSetAndGetIsThreadSafe) {
    HashMap<int> m;
    constexpr int kThreads = 8;
    constexpr int kPerThread = 200;
    std::vector<std::thread> threads;
    for (int t = 0; t < kThreads; ++t) {
        threads.emplace_back([&, t] {
            for (int i = 0; i < kPerThread; ++i) {
                m.set("t" + std::to_string(t) + "_" + std::to_string(i), t * 1000 + i);
            }
        });
    }
    for (auto &th : threads) th.join();
    EXPECT_EQ(m.size(), static_cast<size_t>(kThreads * kPerThread));
    for (int t = 0; t < kThreads; ++t) {
        for (int i = 0; i < kPerThread; ++i) {
            int out = -1;
            ASSERT_TRUE(m.get("t" + std::to_string(t) + "_" + std::to_string(i), out));
            EXPECT_EQ(out, t * 1000 + i);
        }
    }
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
