/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_putnbr.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/23 11:10:44 by dasantos          #+#    #+#             */
/*   Updated: 2025/11/07 12:06:59 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

static void print_nbr(long n)
{
	char c;

	if (n >= 10)
		print_nbr(n / 10);
	c = (n % 10) + '0';
	write(1, &c, 1);
}

static int count_digits(long n)
{
	int count;

	count = 1;
	while (n >= 10)
	{
		n /= 10;
		count++;
	}
	return (count);
}

int ft_putnbr(int n)
{
	long nb;

	int count;

	nb = n;
	count = 0;
	if (nb < 0)
	{
		write(1, "-", 1);
		nb = -nb;
		count++;
	}
	print_nbr(nb);
	count += count_digits(nb);
	return (count);
}
