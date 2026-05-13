/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_substr.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:22:25 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 09:15:17 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdlib.h>

char	*ft_substr(char const *s, unsigned int start, size_t len)
{
	char	*result;
	size_t	i;
	size_t	result_len;

	if (!s)
		return (0);
	result_len = ft_strlen(s);
	if (start >= result_len)
		return (ft_strdup(""));
	if (len > result_len - start)
		len = result_len - start;
	result = (char *)malloc(len + 1);
	if (!result)
		return (0);
	i = 0;
	while (i < len)
	{
		result[i] = s[start + i];
		i++;
	}
	result[i] = '\0';
	return (result);
}
/*
#include <stdio.h>

int	main(void)
{
	char	*sub;

	sub = ft_substr("libft is cool", 6, 2);
	printf("Substring: %s\n", sub);
	free(sub);
	return (0);
}
*/