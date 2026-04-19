/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push_swap.h                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/29 11:04:17 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 11:23:21 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef PUSH_SWAP_H
# define PUSH_SWAP_H

# include "./ft_printf/ft_printf.h"
# include <limits.h>
# include <stdbool.h>
# include <stdlib.h>

typedef struct s_stack_node
{
	int					value;
	int					index;
	int					push_cost;
	bool				above_median;
	bool				cheapest;

	struct s_stack_node	*next;
	struct s_stack_node	*prev;
	struct s_stack_node	*target_node;
}						t_stack_node;

/* Split functions */
char					**ft_split(char const *s, char c);

/* Stack initialization and validation */
void					fill_stack_a(t_stack_node **stack, char **args);
t_stack_node			*find_last_node(t_stack_node *stack);
bool					error_syntax(char *str);
bool					error_duplicate(t_stack_node *stack, int n);
void					free_errors(t_stack_node **stack);

/* Stack operations */
void					sa(t_stack_node **stack_a, bool print);
void					pb(t_stack_node **stack_b, t_stack_node **stack_a,
							bool print);
void					pa(t_stack_node **stack_a, t_stack_node **stack_b,
							bool print);
void					ra(t_stack_node **stack_a, bool print);
void					rra(t_stack_node **stack_a, bool print);
void					rb(t_stack_node **stack_b, bool print);
void					rrb(t_stack_node **stack_b, bool print);
void					rotate_both(t_stack_node **stack_a,
							t_stack_node **stack_b, t_stack_node *node_a,
							t_stack_node *node_b);
void					reverse_rotate_both(t_stack_node **stack_a,
							t_stack_node **stack_b, t_stack_node *node_a,
							t_stack_node *node_b);

/* Stack utils */
bool					stack_sorted(t_stack_node *stack);
int						stack_len(t_stack_node *stack);
t_stack_node			*find_min(t_stack_node *stack);
t_stack_node			*find_max(t_stack_node *stack);
void					free_stack(t_stack_node **stack);
t_stack_node			*get_cheapest(t_stack_node *stack);
void					prep_for_push(t_stack_node **stack,
							t_stack_node *top_node, char stack_name);

/* Node setup and analysis */
void					current_index(t_stack_node *stack);
void					fill_nodes_a(t_stack_node *a, t_stack_node *b);
void					fill_nodes_b(t_stack_node *a, t_stack_node *b);
void					cost_a(t_stack_node *a, t_stack_node *b);
void					set_cheapest(t_stack_node *stack);

/* Sort algorithms */
void					sort_three(t_stack_node **stack_a);
void					sort_stacks(t_stack_node **stack_a,
							t_stack_node **stack_b);
void					move_a_to_b(t_stack_node **stack_a,
							t_stack_node **stack_b);
void					move_b_to_a(t_stack_node **stack_a,
							t_stack_node **stack_b);
void					min_on_top(t_stack_node **stack_a);

#endif
