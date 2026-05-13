/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   get_next_line.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/03 12:23:58 by dasantos          #+#    #+#             */
/*   Updated: 2025/12/03 14:27:04 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "get_next_line.h"

char	*remove_past_line(char *backup)
{
	int		i;
	int		j;
	char	*new_backup;

	i = 0;
	j = 0;
	while (backup[i] && backup[i] != '\n')
		i++;
	if (!backup[i])
		return (free(backup), NULL);
	new_backup = malloc(ft_strlen(backup) - i + 1);
	if (!new_backup)
		return (NULL);
	i++;
	while (backup[i])
		new_backup[j++] = backup[i++];
	new_backup[j] = '\0';
	free(backup);
	return (new_backup);
}

char	*process_line(char *backup)
{
	int		i;
	char	*line;

	i = 0;
	if (!backup || !backup[0])
		return (NULL);
	while (backup[i] && backup[i] != '\n')
		i++;
	if (backup[i] == '\n')
		i++;
	line = malloc(i + 1);
	if (!line)
		return (NULL);
	ft_strncpy(line, backup, i);
	line[i] = '\0';
	return (line);
}

char	*get_next_line(int fd)
{
	static char	*backup;
	char		*buffer;
	char		*result;
	ssize_t		bytes_read;

	if (fd < 0 || BUFFER_SIZE <= 0)
		return (NULL);
	buffer = malloc(BUFFER_SIZE + 1);
	if (!buffer)
		return (NULL);
	bytes_read = 1;
	while (!ft_strchr(backup, '\n') && bytes_read > 0)
	{
		bytes_read = read(fd, buffer, BUFFER_SIZE);
		if (bytes_read < 0)
			return (free(buffer), free(backup), NULL);
		buffer[bytes_read] = '\0';
		backup = ft_strjoin(backup, buffer);
	}
	free(buffer);
	result = process_line(backup);
	backup = remove_past_line(backup);
	return (result);
}
/*
int	main(void)
{
	FILE	*file;
	int		fd;
	char	*line;

	file = fopen("file.txt", "r");
	if (!file)
		return (1);
	fd = fileno(file);
	while ((line = get_next_line(fd)) != NULL)
	{
		printf("%s", line);
		free(line);
	}
	fclose(file);
	return (0);
}
*/