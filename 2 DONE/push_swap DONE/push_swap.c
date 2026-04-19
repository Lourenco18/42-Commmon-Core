/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   push_swap.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/29 11:53:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/01/15 10:35:59 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static void	free_split(char **split)
{
	int	i;

	if (!split)
		return ;
	i = 0;
	while (split[i])
	{
		free(split[i]);
		i++;
	}
	free(split);
}

static void	init_stacks(t_stack_node **a, char **split_args, char **argv,
		int argc)
{
	if (argc == 2)
		fill_stack_a(a, split_args);
	else
		fill_stack_a(a, argv + 1);
}

static void	sort_stack(t_stack_node **a, t_stack_node **b)
{
	if (stack_len(*a) == 2)
		sa(a, true);
	else if (stack_len(*a) == 3)
		sort_three(a);
	else
		sort_stacks(a, b);
}

int	main(int argc, char **argv)
{
	t_stack_node	*a;
	t_stack_node	*b;
	char			**split_args;

	a = NULL;
	b = NULL;
	split_args = NULL;
	if (argc == 1 || (argc == 2 && !argv[1][0]))
		return (1);
	if (argc == 2)
		split_args = ft_split(argv[1], ' ');
	init_stacks(&a, split_args, argv, argc);
	if (!stack_sorted(a))
		sort_stack(&a, &b);
	free_stack(&a);
	if (split_args)
		free_split(split_args);
	return (0);
}
