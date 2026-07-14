/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_isdigit.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/13 11:28:38 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/21 08:48:08 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

int	ft_isdigit(int c)
{
	if (c >= '0' && c <= '9')
	{
		return (1);
	}
	return (0);
}
/*
#include <stdio.h>

int	main(void)
{
	printf("ft_isdigit('0') = %d\n", ft_isdigit('0'));
	printf("ft_isdigit('9') = %d\n", ft_isdigit('9'));
	printf("ft_isdigit('a') = %d\n", ft_isdigit('a'));
	return (0);
}
*/
