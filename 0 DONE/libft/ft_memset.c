/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memset.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/13 11:47:23 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 09:19:40 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stddef.h>

void	*ft_memset(void *b, int c, size_t len)
{
	unsigned char	*p;

	p = (unsigned char *)b;
	while (len--)
		*p++ = (unsigned char)c;
	return (b);
}

/*
#include <stdio.h>

int	main(void)
{
	char	buffer[10];

	ft_memset(buffer, 'A', 5);
	buffer[5] = '\0';
	printf("Memset: %s\n", buffer);
	return (0);
}
*/
