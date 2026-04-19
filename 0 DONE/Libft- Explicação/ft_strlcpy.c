/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strlcpy.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/14 14:30:26 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 14:05:46 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

// copia src para dst garantindo que o tamanho nao exceda dstsize
unsigned int ft_strlcpy(char *dst, const char *src, int dstsize)
{
    int srclen;
    int i;

    srclen = ft_strlen(src); // obtém o tamanho de src
    if (dstsize == 0)        // se o tamanho do destino for 0, nao copia nada
        return (srclen);     // retorna o tamanho de src

    i = 0;
    while (i + 1 < dstsize && src[i]) // copia src para dst garantindo que o tamanho nao exceda dstsize
    {
        dst[i] = src[i]; // copia caractere por caractere de src para dst
        i++;
    }
    dst[i] = '\0';
    return (srclen);
}