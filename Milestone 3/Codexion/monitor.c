/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   monitor.c                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:56 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/05 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	check_burnout(t_sim *sim)
{
	int			i;
	long long	now;
	long long	deadline;

	now = get_time_ms();
	i = 0;
	while (i < sim->n_coders)
	{
		deadline = sim->coders[i].last_compile_start + sim->time_to_burnout;
		if (now >= deadline && sim->coders[i].state != STATE_COMPILING)
		{
			log_state(sim, sim->coders[i].id, "burned out");
			sim->burnout_coder_id = sim->coders[i].id;
			return (i + 1);
		}
		i++;
	}
	return (0);
}

static int	check_all_done(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n_coders)
	{
		if (sim->coders[i].compile_count < sim->n_compiles_required)
			return (0);
		i++;
	}
	return (1);
}

static void	broadcast_all(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n_coders)
	{
		pthread_mutex_lock(&sim->dongles[i].mutex);
		pthread_cond_broadcast(&sim->dongles[i].cond);
		pthread_mutex_unlock(&sim->dongles[i].mutex);
		i++;
	}
}

static void	stop_sim(t_sim *sim)
{
	pthread_mutex_lock(&sim->stop_mutex);
	sim->stopped = 1;
	sim->end_time_ms = get_time_ms();
	pthread_mutex_unlock(&sim->stop_mutex);
	broadcast_all(sim);
}

void	*monitor_routine(void *arg)
{
	t_sim	*sim;

	sim = (t_sim *)arg;
	while (1)
	{
		usleep(500);
		if (sim_is_stopped(sim))
			break ;
		if (check_all_done(sim))
		{
			stop_sim(sim);
			break ;
		}
		if (check_burnout(sim))
		{
			stop_sim(sim);
			break ;
		}
	}
	return (NULL);
}
