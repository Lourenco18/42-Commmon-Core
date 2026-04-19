/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strjoin.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:25:14 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 14:00:01 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdlib.h>

// junta duas strings em uma nova string alocada dinamicamente
char *ft_strjoin(char const *s1, char const *s2)
{
    char *joined;
    int len1;
    int len2;
    int i;

    if (!s1 || !s2)
        return (0);
    len1 = ft_strlen(s1); // tamanho de ambas as strings
    len2 = ft_strlen(s2);
    joined = (char *)malloc(len1 + len2 + 1); // alloca nova string com tamanho suficiente para ambas as strings e o caractere nulo
    if (!joined)
        return (0);
    i = 0;
    while (*s1) // copia os caracteres de s1 para a nova string
        joined[i++] = *s1++;
    while (*s2) // copia os caracteres de s2 para a nova string
        joined[i++] = *s2++;
    joined[i] = '\0';
    return (joined);
}
