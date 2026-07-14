/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   get_next_line_utils.c                              :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/03 12:19:52 by dasantos          #+#    #+#             */
/*   Updated: 2025/11/03 12:37:33 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "get_next_line.h"

size_t	ft_strlen(const char *s)
{
	size_t	size;

	if (!s)
		return (0);
	size = 0;
	while (s[size])
		size++;
	return (size);
}

char	*ft_strchr(const char *s, int c)
{
	unsigned char	ch;

	if (!s)
		return (NULL);
	ch = (unsigned char)c;
	while (*s)
	{
		if ((unsigned char)*s == ch)
			return ((char *)s);
		s++;
	}
	if (ch == '\0')
		return ((char *)s);
	return (NULL);
}
char	*ft_strjoin(char *s1, char *s2)
{
	char	*joined;
	int		len1;
	int		len2;
	int		i;
	int		j;

	if (!s2)
		return (NULL);
	len1 = ft_strlen(s1);
	len2 = ft_strlen(s2);
	joined = malloc(len1 + len2 + 1);
	if (!joined)
		return (free(s1), NULL);
	i = 0;
	while (s1 && s1[i])
	{
		joined[i] = s1[i];
		i++;
	}
	j = 0;
	while (s2[j])
		joined[i++] = s2[j++];
	joined[i] = '\0';
	free(s1);
	return (joined);
}
char	*ft_strncpy(char *dest, const char *src, unsigned int n)
{
	unsigned int	i;

	i = 0;
	while (src[i] != '\0' && i < n)
	{
		dest[i] = src[i];
		i++;
	}
	while (i < n)
	{
		dest[i] = '\0';
		i++;
	}
	return (dest);
}

char	*ft_strdup(const char *s)
{
	char	*dup;
	size_t	len;
	size_t	i;

	if (!s)
		return (NULL);
	len = ft_strlen(s);
	dup = malloc(len + 1);
	if (!dup)
		return (NULL);
	i = 0;
	while (i < len)
	{
		dup[i] = s[i];
		i++;
	}
	dup[i] = '\0';
	return (dup);
}
