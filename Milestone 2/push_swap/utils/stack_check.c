/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   stack_check.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/01/02 12:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/02 11:54:01 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

bool	stack_sorted(t_stack_node *stack)
{
	if (!stack)
		return (1);
	while (stack->next)
	{
		if (stack->value > stack->next->value)
			return (false);
		stack = stack->next;
	}
	return (true);
}

int	stack_len(t_stack_node *stack)
{
	int	len;

	len = 0;
	while (stack)
	{
		len++;
		stack = stack->next;
	}
	return (len);
}

bool	error_syntax(char *str)
{
	int	i;

	i = 0;
	if (!str || str[0] == '\0')
		return (true);
	if (str[i] == '+' || str[i] == '-')
		i++;
	if (!str[i])
		return (true);
	while (str[i])
	{
		if (str[i] < '0' || str[i] > '9')
			return (true);
		i++;
	}
	return (false);
}

bool	error_duplicate(t_stack_node *stack, int n)
{
	while (stack)
	{
		if (stack->value == n)
			return (true);
		stack = stack->next;
	}
	return (false);
}
