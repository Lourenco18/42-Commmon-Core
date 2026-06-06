/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sim_init.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:07:09 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/05 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	init_mutexes(t_sim *sim)
{
	if (pthread_mutex_init(&sim->stop_mutex, NULL) != 0)
		return (0);
	if (pthread_mutex_init(&sim->log_mutex, NULL) != 0)
	{
		pthread_mutex_destroy(&sim->stop_mutex);
		return (0);
	}
	return (1);
}

static int	init_dongles(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n_coders)
	{
		if (!dongle_init(&sim->dongles[i], sim))
		{
			while (--i >= 0)
				dongle_destroy(&sim->dongles[i]);
			return (0);
		}
		i++;
	}
	return (1);
}

static void	init_coders(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n_coders)
	{
		sim->coders[i].id = i + 1;
		sim->coders[i].compile_count = 0;
		sim->coders[i].state = STATE_WAITING;
		sim->coders[i].sim = sim;
		sim->coders[i].last_compile_start = sim->start_time_ms;
		sim->coders[i].deadline = sim->start_time_ms + sim->time_to_burnout;
		sim->coders[i].left_dongle = i;
		if (sim->n_coders == 1)
			sim->coders[i].right_dongle = 0;
		else
			sim->coders[i].right_dongle = (i + 1) % sim->n_coders;
		i++;
	}
}

static int	alloc_sim(t_sim *sim)
{
	sim->coders = (t_coder *)malloc(sizeof(t_coder) * (size_t)sim->n_coders);
	if (!sim->coders)
		return (0);
	memset(sim->coders, 0, sizeof(t_coder) * (size_t)sim->n_coders);
	sim->dongles = (t_dongle *)malloc(sizeof(t_dongle) * (size_t)sim->n_coders);
	if (!sim->dongles)
	{
		free(sim->coders);
		return (0);
	}
	memset(sim->dongles, 0, sizeof(t_dongle) * (size_t)sim->n_coders);
	return (1);
}

int	sim_init(t_sim *sim)
{
	sim->stopped = 0;
	sim->burnout_coder_id = 0;
	sim->start_time_ms = get_time_ms();
	sim->end_time_ms = 0;
	if (!init_mutexes(sim))
		return (0);
	if (!alloc_sim(sim))
	{
		pthread_mutex_destroy(&sim->log_mutex);
		pthread_mutex_destroy(&sim->stop_mutex);
		return (0);
	}
	if (!init_dongles(sim))
	{
		free(sim->dongles);
		free(sim->coders);
		pthread_mutex_destroy(&sim->log_mutex);
		pthread_mutex_destroy(&sim->stop_mutex);
		return (0);
	}
	init_coders(sim);
	return (1);
}
