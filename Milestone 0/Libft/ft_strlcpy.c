/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strlcpy.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/14 14:30:26 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 09:09:07 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

size_t	ft_strlcpy(char *dst, const char *src, size_t dstsize)
{
	size_t	srclen;
	size_t	i;

	srclen = ft_strlen(src);
	if (dstsize == 0)
		return (srclen);
	i = 0;
	while (i + 1 < dstsize && src[i])
	{
		dst[i] = src[i];
		i++;
	}
	dst[i] = '\0';
	return (srclen);
}
/*
#include <stdio.h>

int	main(void)
{
	char	dst[10];
	size_t	ret;

	ret = ft_strlcpy(dst, "Hello", sizeof(dst));
	printf("Copied: %s (return: %zu)\n", dst, ret);
	return (0);
}
*/
