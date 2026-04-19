/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_isalnum.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/13 11:29:03 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/18 15:20:14 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

// verifica se é um digito ou um alpha
// tambem podemos usar as duas funcoes ft_isdigit e ft_is_alpha
int ft_isalnum(int c)
{
    if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))
    {
        return (1);
    }
    return (0);
}