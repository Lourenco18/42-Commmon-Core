/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   split.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/12/29 12:15:00 by dasantos          #+#    #+#             */
/*   Updated: 2025/12/29 12:15:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "push_swap.h"

static int	count_substrings(char const *s, char separator)
{
	int	i;
	int	substring_count;

	i = 0;
	substring_count = 0;
	if (!s)
		return (0);
	while (s[i])
	{
		while (s[i] && s[i] == separator)
			i++;
		if (!s[i])
			break ;
		substring_count++;
		while (s[i] && s[i] != separator)
			i++;
	}
	return (substring_count);
}

static void	free_result(char **result, int j)
{
	while (j > 0)
		free(result[--j]);
}

static char	*allocate_substring(const char *s, int start, int end)
{
	char	*substr;
	int		len;
	int		i;

	len = end - start;
	substr = malloc(len + 1);
	if (!substr)
		return (NULL);
	i = 0;
	while (start < end)
		substr[i++] = s[start++];
	substr[i] = '\0';
	return (substr);
}

static int	p_substrings(const char *s, char sep, char **res, int substrings)
{
	int	j;
	int	start;
	int	end;

	j = 0;
	start = 0;
	while (j < substrings)
	{
		while (s[start] && s[start] == sep)
			start++;
		end = start;
		while (s[end] && s[end] != sep)
			end++;
		res[j] = allocate_substring(s, start, end);
		if (!res[j])
			return (free_result(res, j), 0);
		start = end;
		j++;
	}
	res[j] = 0;
	return (1);
}

char	**ft_split(const char *s, char c)
{
	int		substrings;
	char	**result;

	if (!s)
		return (0);
	substrings = count_substrings(s, c);
	result = malloc((substrings + 1) * sizeof(char *));
	if (!result)
		return (0);
	if (!p_substrings(s, c, result, substrings))
	{
		free(result);
		return (0);
	}
	return (result);
}
