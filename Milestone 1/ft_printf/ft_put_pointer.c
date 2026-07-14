/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_put_pointer.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/23 11:11:34 by dasantos          #+#    #+#             */
/*   Updated: 2025/11/07 12:13:57 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

static int print_pointer(unsigned long n)
{
	char *base;
	int count;

	base = "0123456789abcdef";
	count = 0;
	if (n >= 16)
		count += print_pointer(n / 16);
	count += ft_putchar(base[n % 16]);
	return (count);
}

int ft_put_pointer(void *ptr)
{
	unsigned long address;
	int count;

	if (!ptr)
		return (write(1, "(nil)", 5));
	address = (unsigned long)ptr;
	count = write(1, "0x", 2);
	count += print_pointer(address);
	return (count);
}
