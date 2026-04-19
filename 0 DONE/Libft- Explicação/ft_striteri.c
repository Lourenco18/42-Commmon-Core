/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_striteri.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:27:55 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 13:58:44 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

// void (*f)(unsigned int, char *) - pnteiro para uma funcao que recebe dois argumentos
void ft_striteri(char *s, void (*f)(unsigned int, char *))
{
    int i;

    i = 0;

    if (!s || !f) // verifica se a string ou a funcao sao nulas
        return;
    while (s[i]) // percorre a string de caractere em. caractere e envia para a funcao f
    {
        f(i, &s[i]); // chama a funcao f passando o indice e o endereco do caractere atual
        i++;
    }
}
