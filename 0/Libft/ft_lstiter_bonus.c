/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_lstiter_bonus.c                                 :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/22 10:58:14 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/22 10:58:51 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

void	ft_lstiter(t_list *lst, void (*f)(void *))
{
	t_list	*head;

	head = lst;
	if (!f || !lst)
		return ;
	while (head)
	{
		f(head->content);
		head = head->next;
	}
}

/*
#include <stdio.h> //TODO remove me
#include <stdlib.h>

void	print_lst(t_list *lst)
{
	while (lst)
	{
		printf("%d ", *(int *)lst->content);
		lst = lst->next;
	}
	printf("\n");
}

void	add_wrapper(void *content)
{
	int	*pcontent;

	pcontent = (int *)content;
	(*pcontent)++;
}

int	main(int argc, char **argv)
{
	int	*val;

	t_list	*list, *head;
	list = NULL;
	for (int i = 1; i < argc; i++)
	{
		val = malloc(sizeof(int *));
		*val = atoi(argv[i]);
		head = ft_lstnew(val);
		if (!list)
		{
			list = head;
		}
		else {
			ft_lstadd_back(&list, head);
		}
	}
	printf("before func\n");
	print_lst(list);
	ft_lstiter(list, &add_wrapper);
	printf("after func\n");
	print_lst(list);
	return (0);
}
*/