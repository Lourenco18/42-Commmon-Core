/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_putendl_fd.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/17 11:28:43 by dasantos          #+#    #+#             */
/*   Updated: 2025/10/20 13:53:07 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include <unistd.h>

void ft_putendl_fd(char *s, int fd) // escreve a string s seguida de uma nova linha no file descriptor fd
{
    if (!s)
        return;
    while (*s)
        write(fd, s++, 1);
    write(fd, "\n", 1);
}
