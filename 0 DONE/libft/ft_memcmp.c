/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memcmp.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:19:35 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/22 10:37:57 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stddef.h>

int	ft_memcmp(const void *s1, const void *s2, size_t n)
{
	const unsigned char	*a = (const unsigned char *)s1;
	const unsigned char	*b = (const unsigned char *)s2;

	while (n--)
	{
		if (*a != *b)
			return (*a - *b);
		a++;
		b++;
	}
	return (0);
}
/*
#include <stdio.h>

int	main(void)
{
	printf("memcmp equal = %d\n", ft_memcmp("abc", "abc", 3));
	printf("memcmp diff = %d\n", ft_memcmp("abc", "abd", 3));
	return (0);
}
	*/
