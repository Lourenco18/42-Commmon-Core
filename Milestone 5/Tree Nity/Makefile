# treenity - Makefile
#
# Targets:
#   make / make all   - build bin/server and bin/client
#   make test          - build everything (incl. unit tests) and run:
#                           1) the gtest unit tests (prefix trie + hashmap)
#                           2) the end-to-end integration test (tests/integration_test.sh)
#                         exits non-zero if anything fails.
#   make clean         - remove build artifacts (object files, test binaries)
#   make fclean        - clean + remove bin/server and bin/client
#   make re            - fclean + all

CXX      := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -Wshadow -O2 -pthread
LDFLAGS  := -pthread

SRC_DIR   := src
BUILD_DIR := build
BIN_DIR   := bin
TEST_DIR  := tests

SERVER_BIN := $(BIN_DIR)/server
CLIENT_BIN := $(BIN_DIR)/client

SERVER_SRC := $(SRC_DIR)/server/server.cpp
CLIENT_SRC := $(SRC_DIR)/client/client.cpp

# Headers-only common/ and topic.hpp mean the two translation units above
# are each a single .cpp file; -MMD/-MP still gives us proper header
# dependency tracking so `make` rebuilds when a .hpp changes.
DEPFLAGS = -MMD -MP

GTEST_LIBS := -lgtest -lpthread

.PHONY: all clean fclean re test test-unit test-integration dirs

all: dirs $(SERVER_BIN) $(CLIENT_BIN)

dirs:
	@mkdir -p $(BIN_DIR) $(BUILD_DIR)

$(SERVER_BIN): $(SERVER_SRC) $(wildcard $(SRC_DIR)/common/*.hpp) $(wildcard $(SRC_DIR)/server/*.hpp) | dirs
	$(CXX) $(CXXFLAGS) $(DEPFLAGS) -o $@ $(SERVER_SRC) $(LDFLAGS)

$(CLIENT_BIN): $(CLIENT_SRC) $(wildcard $(SRC_DIR)/common/*.hpp) | dirs
	$(CXX) $(CXXFLAGS) $(DEPFLAGS) -o $@ $(CLIENT_SRC) $(LDFLAGS)

# --- tests -------------------------------------------------------------

$(BUILD_DIR)/test_trie: $(TEST_DIR)/test_trie.cpp $(SRC_DIR)/common/trie.hpp | dirs
	$(CXX) $(CXXFLAGS) -o $@ $(TEST_DIR)/test_trie.cpp $(GTEST_LIBS)

$(BUILD_DIR)/test_hashmap: $(TEST_DIR)/test_hashmap.cpp $(SRC_DIR)/common/hashmap.hpp | dirs
	$(CXX) $(CXXFLAGS) -o $@ $(TEST_DIR)/test_hashmap.cpp $(GTEST_LIBS)

# `make test` is the single entry point an evaluator (or CI) needs: it
# builds the server/client, builds+runs the gtest unit tests, then runs
# the black-box integration test against the real binaries. Any failure
# anywhere makes this target fail.
test: all test-unit test-integration
	@echo ""
	@echo "================================================================"
	@echo " ALL TESTS PASSED"
	@echo "================================================================"

test-unit: $(BUILD_DIR)/test_trie $(BUILD_DIR)/test_hashmap
	@echo "== unit tests: prefix trie =="
	@./$(BUILD_DIR)/test_trie
	@echo ""
	@echo "== unit tests: client hashmap =="
	@./$(BUILD_DIR)/test_hashmap

test-integration: all
	@echo ""
	@echo "== integration test (real server + client binaries) =="
	@chmod +x $(TEST_DIR)/integration_test.sh
	@BUILD_DIR=$(BUILD_DIR) BIN_DIR=$(BIN_DIR) bash $(TEST_DIR)/integration_test.sh

clean:
	rm -rf $(BUILD_DIR)

fclean: clean
	rm -rf $(BIN_DIR)

re: fclean all

-include $(BUILD_DIR)/*.d
