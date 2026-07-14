/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strchr.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:21:13 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/22 09:45:48 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

char	*ft_strchr(const char *s, int c)
{
	unsigned char	ch;

	ch = (unsigned char)c;
	while (*s)
	{
		if ((unsigned char)*s == ch)
			return ((char *)s);
		s++;
	}
	if (ch == '\0')
		return ((char *)s);
	return (0);
}

/*#include <stdio.h>
int	main(void)
{
	const char	*str = "Hello World";

	printf("ft_strchr('o') = %s\n", ft_strchr(str, 'o'));
	printf("ft_strchr('z') = %s\n", ft_strchr(str, 'z') ? ft_strchr(str,
			'z') : "NULL");
	return (0);
}
*/
