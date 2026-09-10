# TAP - The Answer Protocol - top-level Makefile
#
# Build system: plain GNU Make + gcc. Chosen because the project language
# is C and no package manager beyond apt (for GTK3 headers) is needed.
#
# Targets:
#   make / make all      - build server, CLI client, GUI client
#   make deps             - install system dependencies (GTK3 dev headers)
#   make run-server       - run the server on port 4242 with the sample world
#   make run-client        - run the CLI client (connects to 127.0.0.1:4242)
#   make run-client-gui   - run the GUI client
#   make lint             - run cppcheck / gcc -Wall -Wextra static checks
#   make test             - run the automated protocol test suite (tests/test.sh)
#   make clean            - remove build artifacts
#   make fclean           - clean + remove logs
#   make re               - fclean + all

CC       := gcc
STD      := -std=c11
WARN     := -Wall -Wextra
DEFS     := -D_POSIX_C_SOURCE=200809L
CFLAGS   := $(STD) $(WARN) $(DEFS) -O2 -Icommon
GTK_CFLAGS := $(shell pkg-config --cflags gtk+-3.0)
GTK_LIBS   := $(shell pkg-config --libs gtk+-3.0)

BUILD_DIR := build
BIN_DIR   := bin

COMMON_SRCS := common/jsonmin.c
SERVER_SRCS := server/server.c server/world.c common/jsonmin.c common/log.c
CLI_SRCS    := client-cli/cli.c
GUI_SRCS    := client-gui/gui.c common/jsonmin.c

SERVER_BIN := $(BIN_DIR)/tap-server
CLI_BIN    := $(BIN_DIR)/tap-cli
GUI_BIN    := $(BIN_DIR)/tap-gui

.PHONY: all deps run-server run-client run-client-gui lint test clean fclean re help

all: $(SERVER_BIN) $(CLI_BIN) $(GUI_BIN)
	@echo "Build complete:"
	@echo "  $(SERVER_BIN)"
	@echo "  $(CLI_BIN)"
	@echo "  $(GUI_BIN)"

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(SERVER_BIN): $(SERVER_SRCS) common/jsonmin.h common/log.h server/world.h | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $(SERVER_SRCS)

$(CLI_BIN): $(CLI_SRCS) | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $(CLI_SRCS)

$(GUI_BIN): $(GUI_SRCS) common/jsonmin.h | $(BIN_DIR)
	$(CC) $(CFLAGS) $(GTK_CFLAGS) -o $@ $(GUI_SRCS) $(GTK_LIBS)

## deps: install system dependencies needed to build (Debian/Ubuntu).
deps:
	apt-get update
	apt-get install -y build-essential libgtk-3-dev pkg-config cppcheck netcat-openbsd

## run-server: start the server with the bundled sample world on port 4242.
run-server: $(SERVER_BIN)
	mkdir -p logs
	./$(SERVER_BIN) --port 4242 --world world/world.json --log logs/server.log

## run-client: start the CLI client against 127.0.0.1:4242.
run-client: $(CLI_BIN)
	./$(CLI_BIN) --host 127.0.0.1 --port 4242

## run-client-gui: start the GTK3 GUI client.
run-client-gui: $(GUI_BIN)
	./$(GUI_BIN)

## lint: static analysis. Uses cppcheck if available, always runs a strict
## gcc -Wall -Wextra -fsyntax-only pass which fails the build on warnings.
lint:
	@echo "== gcc strict syntax check =="
	$(CC) $(CFLAGS) -Werror -fsyntax-only $(SERVER_SRCS)
	$(CC) $(CFLAGS) -Werror -fsyntax-only $(CLI_SRCS)
	$(CC) $(CFLAGS) $(GTK_CFLAGS) -Werror -fsyntax-only $(GUI_SRCS)
	@echo "== cppcheck (if installed) =="
	@command -v cppcheck >/dev/null 2>&1 && \
		cppcheck --enable=warning,performance,portability --error-exitcode=0 \
		--suppress=missingIncludeSystem common server client-cli client-gui \
		|| echo "(cppcheck not installed - skip with 'make deps')"

## test: run the full automated test suite (starts its own server instance).
test: all
	bash tests/test.sh

clean:
	rm -rf $(BIN_DIR)
	find . -name '*.o' -delete

fclean: clean
	rm -rf logs/*.log

re: fclean all

help:
	@echo "Available targets: all deps run-server run-client run-client-gui lint test clean fclean re"
