/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   rotate_ops.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 12:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 11:54:01 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static void	rotate(t_stack_node **stack)
{
	t_stack_node	*first;
	t_stack_node	*last;

	if (!stack || !*stack || !(*stack)->next)
		return ;
	first = *stack;
	last = find_last_node(*stack);
	*stack = first->next;
	(*stack)->prev = NULL;
	first->next = NULL;
	last->next = first;
	first->prev = last;
}

static void	reverse_rotate(t_stack_node **stack)
{
	t_stack_node	*last;
	t_stack_node	*before_last;

	if (!stack || !*stack || !(*stack)->next)
		return ;
	last = find_last_node(*stack);
	before_last = last->prev;
	if (before_last)
		before_last->next = NULL;
	last->prev = NULL;
	last->next = *stack;
	(*stack)->prev = last;
	*stack = last;
}

void	ra(t_stack_node **stack_a, bool print)
{
	rotate(stack_a);
	if (print)
		ft_printf("ra\n");
}

void	rb(t_stack_node **stack_b, bool print)
{
	rotate(stack_b);
	if (print)
		ft_printf("rb\n");
}

void	rra(t_stack_node **stack_a, bool print)
{
	reverse_rotate(stack_a);
	if (print)
		ft_printf("rra\n");
}
