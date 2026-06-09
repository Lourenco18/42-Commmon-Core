NAME    = codexion

CC      = cc
CFLAGS  = -Wall -Wextra -Werror -pthread

SRCDIR  = .
SRCS    = $(SRCDIR)/main.c \
          $(SRCDIR)/args.c \
          $(SRCDIR)/time_utils.c \
          $(SRCDIR)/pqueue.c \
          $(SRCDIR)/dongle.c \
          $(SRCDIR)/log.c \
          $(SRCDIR)/monitor.c \
          $(SRCDIR)/coder.c \
          $(SRCDIR)/sim.c \
          $(SRCDIR)/sim_init.c \
          $(SRCDIR)/sim_stats.c \
          $(SRCDIR)/pqueue_utils.c \
          $(SRCDIR)/dongle_utils.c

OBJDIR = obj
OBJS    = $(patsubst $(SRCDIR)/%.c,$(OBJDIR)/%.o,$(SRCS))

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) -o $(NAME) $(OBJS)

$(OBJDIR)/%.o: $(SRCDIR)/%.c $(SRCDIR)/codexion.h
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS)
	rm -rf $(OBJDIR)
	rm -f $(NAME)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re

SANITIZE_FLAGS = -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer

.PHONY: asan memcheck

test-mac: clean
	$(MAKE) CFLAGS="$(CFLAGS) $(SANITIZE_FLAGS)" all

memcheck: all
	@command -v valgrind >/dev/null 2>&1 || { echo "valgrind not found; install it or use 'make test-mac'"; exit 1; }
	valgrind --leak-check=full --show-leak-kinds=all ./$(NAME)

.PHONY: install
install:
	@echo "Checking for package managers and installing test deps..."
	# Prefer apt-get (Linux) when available
	@command -v apt-get >/dev/null 2>&1 && { echo "Detected apt-get — installing valgrind and build-essential"; sudo apt-get update && sudo apt-get install -y valgrind build-essential || true; echo "Done (or already installed)."; exit 0; }
	# Fall back to Homebrew on macOS (tolerate failures)
	@command -v brew >/dev/null 2>&1 && { echo "Detected Homebrew — attempting to install valgrind (may not be supported on macOS)"; brew install valgrind || true; echo "Done (or already installed / unsupported)."; exit 0; }
	@echo "No supported package manager found. Please install 'valgrind' (and build tools) manually. For Debian/Ubuntu: 'sudo apt-get install valgrind build-essential'.";

.PHONY: docker-test
docker-test:
	@command -v docker >/dev/null 2>&1 || { echo "docker not found; install Docker to use this target"; exit 1; }
	@echo "Running tests inside Ubuntu container (will install valgrind inside container)..."
	docker run --rm -v "$$PWD":/work -w /work ubuntu:22.04 bash -lc "apt-get update && apt-get install -y build-essential valgrind && make clean && make && valgrind --leak-check=full --show-leak-kinds=all ./codexion 5 1000 100 100 50 3 200 fifo"

TIE_SRCS = test_tiebreaker.c test_tiebreaker_main.c \
           pqueue.c pqueue_utils.c time_utils.c
TIE_OBJS = $(patsubst %.c,$(OBJDIR)/tie_%.o,$(TIE_SRCS))
 
$(OBJDIR)/tie_%.o: %.c
	@mkdir -p $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@
 
test_tie: $(TIE_OBJS)
	$(CC) $(CFLAGS) -o test_tie $(TIE_OBJS)
	./test_tie
 
.PHONY: test_tie
 
tie:
	@python3 test_tie.py
 
.PHONY: tie
 