/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_substr.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:22:25 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 15:28:19 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdlib.h>

char *ft_substr(char const *s, int start, int len)
{
    char *result;
    int i;
    int result_len;

    if (!s)
        return (0);
    result_len = ft_strlen(s);
    if (start >= result_len)          // se o indice inicial for maior que o tamanho da string original
        return (ft_strdup(""));       // retorna uma string vazia
    if (len > result_len - start)     // ajusta o comprimento se exceder o tamanho disponivel
        len = result_len - start;     // calcula o comprimento maximo possivel
    result = (char *)malloc(len + 1); // aloca memoria para o result mais o caractere nulo
    if (!result)
        return (0);
    i = 0;
    while (i < len)
    {
        result[i] = s[start + i]; // copia os caracteres da string original para a result
        i++;
    }
    result[i] = '\0';
    return (result);
}
