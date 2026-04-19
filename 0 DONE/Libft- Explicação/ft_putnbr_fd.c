/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_putnbr_fd.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:28:57 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 13:53:07 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>
#include "libft.h"

// escrever um numerio inteiro n no file descriptor fd
void ft_putnbr_fd(int n, int fd)
{
    long num = n;
    if (num < 0) // caso seja negativo colocar o sinal de menos
    {
        ft_putchar_fd('-', fd);
        num = -num; // tornar o valor positivo
    }
    if (num >= 10) // se for maior ou igual a 10, chamar recursivamente a funcao para o numero dividido por 10
        ft_putnbr_fd(num / 10, fd);
    ft_putchar_fd((num % 10) + '0', fd); // escrever o digito mais a direita
}
