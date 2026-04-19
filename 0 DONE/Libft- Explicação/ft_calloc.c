/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_calloc.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:18:25 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/18 15:20:14 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdlib.h>
// n_element - numero de elementos a alocar
// size - tamanho em bytes de cada elemento, por exemplo - sizeof(int)
void *ft_calloc(unsigned int n_element, unsigned int size)
{
    void *ptr; // endereço de memoria alocada
    // caso seja overflow retorna-se '0'
    if (n_element && size && n_element > 4294967295U / size) // prevenir o overflow, 4294967295U- maior valor possivel para um "unsigned imt"
        return (0);
    ptr = malloc(n_element * size); // aloca um bloco de memoria com o o tamanho (n_element *size)
    if (!ptr)                       // se malloc falhar return 0
        return (0);
    ft_bzero(ptr, n_element * size); // coloca tudo em zero
    // retornar o ponteiro que aponta para a memoria alocada
    return (ptr);
}
