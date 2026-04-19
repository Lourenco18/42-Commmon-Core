/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strrchr.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/22 10:58:42 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/22 10:58:51 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

char	*ft_strrchr(const char *s, int c)
{
	int	i;
	int	last_c;

	last_c = -1;
	i = 0;
	while (s[i])
	{
		if ((unsigned char)s[i] == (unsigned char)c)
			last_c = i;
		i++;
	}
	if ((unsigned char)c == 0)
		return ((char *)(s + i));
	if (last_c < 0)
		return (NULL);
	else
		return ((char *)&s[last_c]);
}

/*
#include <stdio.h>
#include <string.h>

int	main(void)
{
	char	word[40] = "Ola tudo bem?";

	printf("==>O meu<==\n");
	printf("output: %s\n\n", ft_strrchr(word, '0'));
	printf("==>O original<==\n");
	printf("output: %s\n\n", strrchr(word, '0'));
	return (0);
}
*/