/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   get_cheapest.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 12:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 11:54:01 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

t_stack_node	*get_cheapest(t_stack_node *stack)
{
	t_stack_node	*cheapest;
	long			best_cost;

	cheapest = NULL;
	best_cost = LONG_MAX;
	while (stack)
	{
		if (stack->cheapest || stack->push_cost < best_cost)
		{
			best_cost = stack->push_cost;
			cheapest = stack;
		}
		stack = stack->next;
	}
	return (cheapest);
}
