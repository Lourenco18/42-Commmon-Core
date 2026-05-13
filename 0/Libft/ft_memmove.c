/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memmove.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/22 10:58:38 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/22 10:58:51 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

void	*ft_memmove(void *dest, const void *src, size_t n)
{
	size_t	i;

	i = 0;
	if (!dest && !src)
		return (NULL);
	if (dest < src)
		dest = ft_memcpy(dest, src, n);
	else
	{
		i = n;
		while (i > 0)
		{
			i--;
			*(unsigned char *)(dest + i) = *(unsigned char *)(src + i);
		}
	}
	return (dest);
}

/*
#include <string.h>
#include <stdio.h>

int	main(void)
{
	char	str[100] = "Learningisfun";
	char	str1[100] = "Learningisfun";

	char *first, *second;
	first = str;
	second = str;
	memmove(second + 8, first, 10);
	printf("==>memmove original <==\n%s\n", str);
	first = str1;
	second = str1;
	ft_memmove(second + 8, first, 10);
	printf("==>memmove meu <==\n%s\n", str1);
	return (0);
}
*/