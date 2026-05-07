NAME    = codexion

CC      = cc
CFLAGS  = -Wall -Wextra -Werror -pthread

SRCDIR  = coders
SRCS    = $(SRCDIR)/main.c \
          $(SRCDIR)/args.c \
          $(SRCDIR)/time_utils.c \
          $(SRCDIR)/pqueue.c \
          $(SRCDIR)/dongle.c \
          $(SRCDIR)/log.c \
          $(SRCDIR)/monitor.c \
          $(SRCDIR)/coder.c \
          $(SRCDIR)/sim.c

OBJS    = $(SRCS:.c=.o)

all: $(NAME)

$(NAME): $(OBJS)
	$(CC) $(CFLAGS) -o $(NAME) $(OBJS)

$(SRCDIR)/%.o: $(SRCDIR)/%.c $(SRCDIR)/codexion.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
