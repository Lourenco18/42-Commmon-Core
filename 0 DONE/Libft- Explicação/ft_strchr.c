    /* ************************************************************************** */
    /*                                                                            */
    /*                                                        :::      ::::::::   */
    /*   ft_strchr.c                                        :+:      :+:    :+:   */
    /*                                                    +:+ +:+         +:+     */
    /*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
    /*                                                +#+#+#+#+#+   +#+           */
    /*   Created: 2025/10/15 12:21:13 by dasantos          #+#    #+#             */
    /*   Updated: 2025/10/20 13:50:07 by dasantos         ###   ########.fr       */
    /*                                                                            */
    /* ************************************************************************** */

    // encontra a primeira ocorrencia do caractere c na string s
    char *ft_strchr(const char *s, int c)
    {
        while (*s)
        {
            if (*s == (char)c)
                return (char *)s; // retorna o ponteiro para a primeira ocorrencia de c
            s++;
        }
        if (c == '\0')
            return (char *)s;
        return (0);
    }