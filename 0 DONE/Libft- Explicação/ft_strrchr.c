/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strrchr.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:21:42 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 15:03:52 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// encontra a ultima ocorrencia do caractere c na string s
char *ft_strrchr(const char *s, int c)
{
    const char *last = (0); // ponteiro para armazenar a ultima ocorrencia encontrada
    while (*s)
    {
        if (*s == (char)c) // se o caractere atual for igual a c
            last = s;      // atualiza o ponteiro last para a posicao atual
        s++;
    }
    if (c == '\0')
        return (char *)s;
    return (char *)last;
}