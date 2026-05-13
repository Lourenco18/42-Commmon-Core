/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   get_next_line.h                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/03 12:20:18 by dasantos          #+#    #+#             */
/*   Updated: 2025/11/03 12:37:33 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef GET_NEXT_LINE_H
# define GET_NEXT_LINE_H

# include <stddef.h>
# include <stdio.h>
# include <stdlib.h>
# include <unistd.h>

# ifndef BUFFER_SIZE
#  define BUFFER_SIZE 42
# endif

size_t	ft_strlen(const char *s);

char	*ft_strchr(const char *s, int c);
char	*ft_strncpy(char *dest, const char *src, unsigned int n);
char	*ft_strdup(const char *s);
char	*get_next_line(int fd);
char	*ft_strjoin(char *s1, char *s2);
#endif
