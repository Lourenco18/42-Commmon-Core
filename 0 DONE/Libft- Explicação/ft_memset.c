/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memset.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/13 11:47:23 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 12:18:57 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

void *ft_memset(void *b, int c, unsigned int len)
{ // b- memoria a ser modificada len- numero de bytes a ser definidos c- valor a definir
    unsigned char *p = (unsigned char *)b;
    while (len--)
        *p++ = (unsigned char)c; // escreve o valor c em cada byte
    return (b);
}