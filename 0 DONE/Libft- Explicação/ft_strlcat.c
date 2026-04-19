/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strlcat.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/14 14:37:06 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 14:02:56 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
// concatena src a dest, garantindo que o tamanho total nao exceda size
unsigned int ft_strlcat(char *dest, const char *src, int size)
{
    int i;
    int j;
    int dest_len;
    int src_len;

    dest_len = ft_strlen(dest);
    src_len = ft_strlen(src);
    if (size <= dest_len) // se o tamanho for menor ou igual ao tamanho da string dest
    {
        return (size + src_len); // retorno o tamanho que era necessário ter dest para ser possivel realizar a operação
    }
    i = dest_len; // inicia a copia a partir do final de dest
    j = 0;
    while (src[j] && i + 1 < size) // copia src para dest ate atingir o tamanho size - 1
    {
        dest[i] = src[j];
        i++;
        j++;
    }
    dest[i] = '\0';
    return (dest_len + src_len); // retorna o tamanho total que a string teria se houvesse espaço suficiente
}