/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strtrim.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:26:00 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 15:28:50 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

static int find(char c, char const *set)
{
    while (*set)
        if (c == *set++)
            return (1);
    return (0);
}

// remover os caracteres  'set' do inicio e do fim de 's1'
char *ft_strtrim(char const *s1, char const *set)
{
    int start;
    int end;

    if (!s1 || !set) // verifica se s1 ou set sao nulos
        return (0);
    start = 0;
    while (s1[start] && find(s1[start], set))
        start++;         // calcula o primeiro indice que nao pertence a set
    end = ft_strlen(s1); // tamanho da string s1
    while (end > start && find(s1[end - 1], set))
        end--; // calcula o ultimo indice que nao pertence a set
    return (ft_substr(s1, start, end - start));
}
