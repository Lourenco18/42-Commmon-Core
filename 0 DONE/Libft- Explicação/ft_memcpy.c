/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memcpy.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/14 13:26:48 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 12:14:01 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// copiar n bytes da area de memoria src para a area de memoria dst
void *ft_memcpy(void *dst, const void *src, int n) // devolve o ponteiro para dst
{
    int i;

    i = 0;
    if (!dst && !src) // caso ambos sejam NULL
        return (0);
    unsigned char *d = (unsigned char *)dst; // converter de void para unsigned char porque nao da para fazer aritmetica com void
    const unsigned char *s = (const unsigned char *)src;

    while (i < n) // enquanto o numero de bytes nao for atingido
    {
        d[i] = s[i]; // copia byte a byte de src para dst
        i++;
    }

    return (dst);
}