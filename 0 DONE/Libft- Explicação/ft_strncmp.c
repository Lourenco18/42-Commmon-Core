/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strncmp.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/15 12:04:30 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 15:23:53 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// compara cada caractere de duas strings ate n caracteres
int ft_strncmp(const char *s1, const char *s2, unsigned int n)
{
    unsigned int i;

    i = 0;
    if (n == 0)
        return (0);
    while (s1[i] && s2[i] && s1[i] == s2[i] && i < n - 1)
        i++;
    return ((unsigned char)s1[i] - (unsigned char)s2[i]);
}
