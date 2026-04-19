/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strnstr.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:08:08 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 15:00:51 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// procura a primeira ocorrencia da string find em main, limitando em len caracteres
char *ft_strnstr(const char *main, const char *find, int len)
{
    int i;
    int j;

    i = 0;

    if (!*find) // se find estiver vazia, retorna main
        return (char *)main;

    while (main[i] && i < len) // enquanto houver caracteres em main e i for menor que len
    {
        j = 0;
        while (main[i + j] == find[j] && (i + j) < len) // compara os caracteres de main e find
        {
            if (!find[j + 1])            // se chegar ao final de find, encontrou a substring
                return (char *)&main[i]; // retorna o ponteiro para a posicao inicial da substring em main
            j++;
        }
        i++;
    }
    return (0);
}
