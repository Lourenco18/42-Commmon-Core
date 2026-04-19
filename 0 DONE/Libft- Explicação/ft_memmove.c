/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memmove.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/14 14:26:02 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 12:14:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// Copia len bytes de src para dst, mesmo que as áreas de memória se sobreponham.
void *ft_memmove(void *dst, const void *src, int len)
{
    unsigned char *d; // converter de void para unsigned char porque nao da para fazer aritmetica com void
    const unsigned char *s;
    int i;

    if (!dst && !src) // se nao houver nada para copiar
        return (0);
    d = (unsigned char *)dst;
    s = (const unsigned char *)src;
    if (d == s) // se forem iguais, nao ha nada para copiar
        return (dst);
    if (d < s) // se o destino estiver antes da fonte na memoria
    {
        i = -1;
        while (++i < len)
            d[i] = s[i]; // copia feita do inicio para o fim
    }
    else // se o destino estiver depois da fonte (áreas sobrepostas)
        while (len--)
            d[len] = s[len]; // copia do fim para o inicio
    return (dst);
}
