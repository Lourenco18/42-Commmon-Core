/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_lstsize_bonus.c                                 :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/22 10:58:33 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/22 10:58:51 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

int	ft_lstsize(t_list *lst)
{
	int	len;

	len = 0;
	while (lst)
	{
		len++;
		lst = lst->next;
	}
	return (len);
}

/*
#include <stdio.h>

int	main(int argc, char **argv)
{
	t_list	*head;
	t_list	*current;

	for (int i = 1; i < argc; i++)
	{
		current = ft_lstnew(argv[i]);
		head = current;
		current = current->next;
	}
	printf("%i\n", ft_lstsize(head));
	return (0);
}
*/