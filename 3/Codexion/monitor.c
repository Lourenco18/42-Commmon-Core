/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   monitor.c                                          :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:56 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:09:47 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/* 4) Rotina de monitorização: detecta burnout ou fim da simulação. */
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

void	*monitor_routine(void *arg)
{
	t_sim	*sim;
	int		should_stop;

	/* 4.1) Monitoriza periodicamente progresso e burnout. */
	sim = (t_sim *)arg;
	while (1)
	{
		usleep(500);

		pthread_mutex_lock(&sim->stop_mutex);
		should_stop = sim->stopped;
		pthread_mutex_unlock(&sim->stop_mutex);

		if (should_stop)
			break ;

		if (check_all_done(sim))
		{
			pthread_mutex_lock(&sim->stop_mutex);
			sim->stopped = 1;
			pthread_mutex_unlock(&sim->stop_mutex);
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
			break ;
		}

		if (check_burnout(sim))
		{
			pthread_mutex_lock(&sim->stop_mutex);
			sim->stopped = 1;
			pthread_mutex_unlock(&sim->stop_mutex);
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
			break ;
		}
	}
	return (NULL);
}
