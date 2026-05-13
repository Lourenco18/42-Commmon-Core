/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_calloc.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:18:25 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 09:24:53 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stddef.h>
#include <stdlib.h>

void	*ft_calloc(size_t n_element, size_t size)
{
	void	*ptr;

	if (n_element && size && n_element > 4294967295U / size)
		return (0);
	ptr = malloc(n_element * size);
	if (!ptr)
		return (0);
	ft_bzero(ptr, n_element * size);
	return (ptr);
}

/*
#include <stdio.h>

int	main(void)
{
	int	*arr;

	arr = (int *)ft_calloc(5, sizeof(int));
	for (int i = 0; i < 5; i++)
		printf("arr[%d] = %d\n", i, arr[i]);
	free(arr);
	return (0);
}
	*/
