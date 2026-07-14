/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strncmp.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:04:30 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 09:04:44 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stddef.h>

int	ft_strncmp(const char *s1, const char *s2, size_t n)
{
	size_t	i;

	i = 0;
	if (n == 0)
		return (0);
	while (s1[i] && s2[i] && s1[i] == s2[i] && i < n - 1)
		i++;
	return ((unsigned char)s1[i] - (unsigned char)s2[i]);
}
/*
#include <stdio.h>

int	main(void)
{
	printf("ft_strncmp(\"abc\", \"abc\", 3) = %d\n", ft_strncmp("abc", "abc",
			3));
	printf("ft_strncmp(\"abc\", \"abd\", 2) = %d\n", ft_strncmp("abc", "abd",
			2));
	printf("ft_strncmp(\"abc\", \"abd\", 3) = %d\n", ft_strncmp("abc", "abd",
			3));
	return (0);
}
*/
