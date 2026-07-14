/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sort_three.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 10:45:26 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 12:00:50 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

void	sort_three(t_stack_node **stack_a)
{
	t_stack_node	*biggest_node;

	biggest_node = find_max(*stack_a);
	if (biggest_node == *stack_a)
		ra(stack_a, true);
	else if (biggest_node == (*stack_a)->next)
		rra(stack_a, true);
	if ((*stack_a)->value > (*stack_a)->next->value)
		sa(stack_a, true);
}
