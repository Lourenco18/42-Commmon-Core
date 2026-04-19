/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   nodes_init_a.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 12:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 12:04:50 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static t_stack_node	*find_best_match_a(t_stack_node *b, int target_val)
{
	t_stack_node	*current;
	t_stack_node	*best;
	long			best_match;

	current = b;
	best = NULL;
	best_match = LONG_MIN;
	while (current)
	{
		if (current->value < target_val && current->value > best_match)
		{
			best_match = current->value;
			best = current;
		}
		current = current->next;
	}
	return (best);
}

static void	set_target_a(t_stack_node *a, t_stack_node *b)
{
	t_stack_node	*target;

	while (a)
	{
		target = find_best_match_a(b, a->value);
		if (target)
			a->target_node = target;
		else
			a->target_node = find_max(b);
		a = a->next;
	}
}

void	cost_a(t_stack_node *a, t_stack_node *b)
{
	int	len_a;
	int	len_b;

	len_a = stack_len(a);
	len_b = stack_len(b);
	while (a)
	{
		a->push_cost = a->index;
		if (!(a->above_median))
			a->push_cost = len_a - (a->index);
		if (a->target_node->above_median)
			a->push_cost += a->target_node->index;
		else
			a->push_cost += len_b - (a->target_node->index);
		a = a->next;
	}
}

void	set_cheapest(t_stack_node *stack)
{
	t_stack_node	*cheapest_node;
	long			cheapest_value;
	t_stack_node	*current;

	if (!stack)
		return ;
	cheapest_value = LONG_MAX;
	cheapest_node = stack;
	current = stack;
	while (current)
	{
		current->cheapest = false;
		if (current->push_cost < cheapest_value)
		{
			cheapest_value = current->push_cost;
			cheapest_node = current;
		}
		current = current->next;
	}
	cheapest_node->cheapest = true;
}

void	fill_nodes_a(t_stack_node *a, t_stack_node *b)
{
	current_index(a);
	current_index(b);
	set_target_a(a, b);
	cost_a(a, b);
	set_cheapest(a);
}
