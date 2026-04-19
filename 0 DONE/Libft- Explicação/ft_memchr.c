/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memchr.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:20:03 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/18 15:39:19 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// procura um byte específico (c) dentro de uma área de memória (s) nos primeiros n bytes.
// Ela percorre um bloco de memória byte a byte e devolve um ponteiro para a primeira ocorrência do caractere procurado (c).
// Se não encontrar, devolve NULL.
void *ft_memchr(const void *s, int c, unsigned int n) // s- ponteiro para a área de memória, c- caractere a ser procurado, n- número de bytes a serem verificados
{
    // converte o ponteiro s para um ponteiro de unsigned char para manipular byte a byte
    const unsigned char *p = (const unsigned char *)s; // ponteiro para percorrer a área de memória
    while (n--)                                        // loop que percorre os primeiros n bytes
    {
        if (*p == (unsigned char)c) // se encontrar o caractere c
            return (void *)p;       // retorna o endereço p desse byte- um ponteiro para a posição encontrada
        p++;                        // avança para o próximo byte
    }
    return (0);
}
