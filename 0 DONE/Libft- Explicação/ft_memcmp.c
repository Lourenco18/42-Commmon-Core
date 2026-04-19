/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memcmp.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:19:35 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/18 15:42:25 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// compara os primeiros n bytes das areas de memoria s1 e s2
int ft_memcmp(const void *s1, const void *s2, unsigned int n)
{
    const unsigned char *a = (const unsigned char *)s1; // cria ponteiro para percorrer s1
    const unsigned char *b = (const unsigned char *)s2; // cria ponteiro para percorrer s2
    while (n--)                                         // loop que percorre os primeiros n bytes
    {
        if (*a != *b)         // se os bytes forem diferentes
            return (*a - *b); // envia a diferença entre os bytes
        a++;
        b++;
    }
    return 0;
}
