/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strmapi.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:27:41 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 09:18:12 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdlib.h>

char	*ft_strmapi(char const *s, char (*f)(unsigned int, char))
{
	char			*new;
	unsigned int	i;

	if (!s || !f)
		return (0);
	new = (char *)malloc(ft_strlen(s) + 1);
	if (!new)
		return (0);
	i = 0;
	while (s[i])
	{
		new[i] = f(i, s[i]);
		i++;
	}
	new[i] = '\0';
	return (new);
}

/*
#include <stdio.h>

char	mapper(unsigned int i, char c) { return (c + i); }

int	main(void)
{
	char	*mapi;

	mapi = ft_strmapi("abc", mapper);
	printf("Mapped: %s\n", mapi);
	free(mapi);
	return (0);
}
*/
