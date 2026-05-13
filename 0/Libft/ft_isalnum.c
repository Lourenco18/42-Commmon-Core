/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_isalnum.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/13 11:29:03 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 08:51:43 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

int	ft_isalnum(int c)
{
	if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0'
			&& c <= '9'))
	{
		return (1);
	}
	return (0);
}
/*
#include <stdio.h>

int	main(void)
{
	printf("ft_isalnum('a') = %d\n", ft_isalnum('a'));
	printf("ft_isalnum('5') = %d\n", ft_isalnum('5'));
	printf("ft_isalnum('!') = %d\n", ft_isalnum('!'));
	return (0);
}
	*/