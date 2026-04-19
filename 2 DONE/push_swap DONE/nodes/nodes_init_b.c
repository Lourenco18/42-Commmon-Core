/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   nodes_init_b.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 12:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 11:58:08 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static t_stack_node	*find_best_match_b(t_stack_node *a, int target_val)
{
	t_stack_node	*current;
	t_stack_node	*best;
	long			best_match;

	current = a;
	best = NULL;
	best_match = LONG_MAX;
	while (current)
	{
		if (current->value > target_val && current->value < best_match)
		{
			best_match = current->value;
			best = current;
		}
		current = current->next;
	}
	return (best);
}

static void	set_target_b(t_stack_node *a, t_stack_node *b)
{
	t_stack_node	*target;

	while (b)
	{
		target = find_best_match_b(a, b->value);
		if (target)
			b->target_node = target;
		else
			b->target_node = find_min(a);
		b = b->next;
	}
}

void	fill_nodes_b(t_stack_node *a, t_stack_node *b)
{
	current_index(a);
	current_index(b);
	set_target_b(a, b);
}
