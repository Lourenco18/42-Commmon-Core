/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strdup.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/20 13:51:30 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 13:52:52 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <stdlib.h>
#include "libft.h"
// duplicar a string src alocando memoria para a nova string
char *ft_strdup(const char *src)
{
    int i;
    int len;
    char *dup;

    len = ft_strlen((char *)src);
    dup = (char *)malloc(sizeof(char) * (len + 1)); // alocar memoria para a nova string
    if (!dup)
        return (0);
    i = 0;
    while (src[i])
    {
        dup[i] = src[i]; // copiar cada caractere de src para dup
        i++;
    }
    dup[i] = '\0';
    return dup;
}
