/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_itoa.c                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:27:25 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/18 15:34:28 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdlib.h>
// tamanho do numero
static int num_len(long n)
{
    int len;
    // conta 1 se for negativo para o '-' e caso seja 0 conta como 1 digito
    if (n <= 0)
        len = 1;
    else
        len = 0;
    // divide por 10 ate n ser 0 contando os digitos
    while (n)
    {
        n /= 10;
        len++;
    }
    return (len);
}
// converter int para string
char *ft_itoa(int n)
{
    long num = n; // nao ter risco de overflow quando n = -2147483648
    int len = num_len(num);
    char *str = malloc(len + 1); // alocar a memoria com o tamanho necessario com um byte extra para o '\0'

    if (!str)
        return (0);
    str[len--] = '\0'; // coloca o terminador no final da string

    if (num == 0)
        str[0] = '0'; // caso especifico caso seja 0
    // se for menor que 0 colocar o sinal - no inicio da string
    if (num < 0)
    {
        str[0] = '-';
        num = -num; // tornar positivo
    }
    // converter cada digito para caractere de tras para frente
    while (num)
    {
        str[len--] = (num % 10) + '0'; // conversao de digito numerico para caractere ASCII
        num /= 10;                     // remover o ultimo digito ja convertido
    }
    return (str);
}
