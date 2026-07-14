/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strlen.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/13 11:38:31 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 08:24:27 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stddef.h>

size_t	ft_strlen(const char *s)
{
	size_t	size;

	size = 0;
	while (s[size])
	{
		size++;
	}
	return (size);
}
/*
int	main(void){

	printf("%zu", ft_strlen("123"));
}
	*/