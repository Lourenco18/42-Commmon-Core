/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:05:59 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/05 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	sim_is_stopped(t_sim *sim)
{
	int	stopped;

	pthread_mutex_lock(&sim->stop_mutex);
	stopped = sim->stopped;
	pthread_mutex_unlock(&sim->stop_mutex);
	return (stopped);
}

static void	get_dongle_order(t_coder *coder, int *first, int *second)
{
	int	left;
	int	right;

	left = coder->left_dongle;
	right = coder->right_dongle;
	if (left < right)
	{
		*first = left;
		*second = right;
	}
	else
	{
		*first = right;
		*second = left;
	}
}

static int	acquire_both(t_coder *coder, int first, int second)
{
	t_sim	*sim;

	sim = coder->sim;
	if (!dongle_acquire(&sim->dongles[first], coder))
		return (0);
	if (sim_is_stopped(sim))
	{
		dongle_release(&sim->dongles[first], coder);
		return (0);
	}
	log_state(sim, coder->id, "has taken a dongle");
	if (!dongle_acquire(&sim->dongles[second], coder))
	{
		dongle_release(&sim->dongles[first], coder);
		return (0);
	}
	if (sim_is_stopped(sim))
	{
		dongle_release(&sim->dongles[second], coder);
		dongle_release(&sim->dongles[first], coder);
		return (0);
	}
	log_state(sim, coder->id, "has taken a dongle");
	return (1);
}

static int	do_compile(t_coder *coder)
{
	t_sim	*sim;
	int		first;
	int		second;

	sim = coder->sim;
	get_dongle_order(coder, &first, &second);
	if (!acquire_both(coder, first, second))
		return (0);
	coder->last_compile_start = get_time_ms();
	coder->deadline = coder->last_compile_start + sim->time_to_burnout;
	coder->state = STATE_COMPILING;
	log_state(sim, coder->id, "is compiling");
	sleep_ms(sim->time_to_compile);
	coder->compile_count++;
	dongle_release(&sim->dongles[second], coder);
	dongle_release(&sim->dongles[first], coder);
	return (1);
}

void	*coder_routine(void *arg)
{
	t_coder	*coder;
	t_sim	*sim;

	coder = (t_coder *)arg;
	sim = coder->sim;
	coder->state = STATE_WAITING;
	while (!sim_is_stopped(sim))
	{
		coder->state = STATE_WAITING;
		if (!do_compile(coder))
			break ;
		if (sim_is_stopped(sim))
			break ;
		coder->state = STATE_DEBUGGING;
		log_state(sim, coder->id, "is debugging");
		sleep_ms(sim->time_to_debug);
		if (sim_is_stopped(sim))
			break ;
		coder->state = STATE_REFACTORING;
		log_state(sim, coder->id, "is refactoring");
		sleep_ms(sim->time_to_refactor);
	}
	return (NULL);
}
