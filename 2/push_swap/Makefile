# Variables
NAME := push_swap
CC := cc
CFLAGS := -Wall -Wextra -Werror
INCLUDES := -I .
OBJDIR := obj

FT_PRINTF_DIR := ft_printf
FT_PRINTF_SRC := $(wildcard $(FT_PRINTF_DIR)/*.c)

SRC := \
	push_swap.c \
	init/stack_init.c \
	ops/swap_push.c \
	ops/rotate_ops.c \
	ops/rotate_both.c \
	nodes/get_cheapest.c \
	nodes/nodes_init_a.c \
	nodes/nodes_init_b.c \
	nodes/index_utils.c \
	utils/stack_find.c \
	utils/stack_check.c \
	utils/split.c \
	utils/free.c \
	sort/sort_three.c \
	sort/sort_stacks.c
OBJ := $(addprefix $(OBJDIR)/,$(SRC:.c=.o))
FT_PRINTF_OBJ := $(patsubst $(FT_PRINTF_DIR)/%.c,$(OBJDIR)/$(FT_PRINTF_DIR)/%.o,$(FT_PRINTF_SRC))

all: $(NAME)

$(NAME): $(OBJ) $(FT_PRINTF_OBJ)
	$(CC) $(CFLAGS) $(INCLUDES) $(OBJ) $(FT_PRINTF_OBJ) -o $(NAME)


# Ensure obj dirs exist before compiling any object
$(OBJ) $(FT_PRINTF_OBJ): | $(OBJDIR) $(OBJDIR)/$(FT_PRINTF_DIR)

$(OBJDIR)/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

$(OBJDIR)/$(FT_PRINTF_DIR)/%.o: $(FT_PRINTF_DIR)/%.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/$(FT_PRINTF_DIR): | $(OBJDIR)
	mkdir -p $(OBJDIR)/$(FT_PRINTF_DIR)

clean:
	rm -rf $(OBJDIR)

fclean: clean
	rm -f $(NAME)

re: fclean all

.PHONY: all clean fclean re
