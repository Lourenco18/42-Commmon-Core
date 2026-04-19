/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   swap_push.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 12:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 11:54:01 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static void	push(t_stack_node **dest, t_stack_node **src)
{
	t_stack_node	*node;

	if (!src || !*src)
		return ;
	node = *src;
	*src = (*src)->next;
	if (*src)
		(*src)->prev = NULL;
	node->next = *dest;
	if (*dest)
		(*dest)->prev = node;
	*dest = node;
	node->prev = NULL;
}

void	sa(t_stack_node **stack_a, bool print)
{
	t_stack_node	*first;
	t_stack_node	*second;

	if (!stack_a || !*stack_a || !(*stack_a)->next)
		return ;
	first = *stack_a;
	second = (*stack_a)->next;
	first->next = second->next;
	if (second->next)
		second->next->prev = first;
	second->next = first;
	second->prev = NULL;
	first->prev = second;
	*stack_a = second;
	if (print)
		ft_printf("sa\n");
}

void	pb(t_stack_node **stack_b, t_stack_node **stack_a, bool print)
{
	push(stack_b, stack_a);
	if (print)
		ft_printf("pb\n");
}

void	pa(t_stack_node **stack_a, t_stack_node **stack_b, bool print)
{
	push(stack_a, stack_b);
	if (print)
		ft_printf("pa\n");
}
