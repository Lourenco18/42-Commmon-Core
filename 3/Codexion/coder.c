/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:05:59 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/11 14:33:15 by dasantos         ###   ########.fr       */
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

/*
** get_dongle_order: protegido por dongle_order_mutex para evitar que dois
** coders adjacentes escolham os mesmos dongles ao mesmo tempo, eliminando
** a corrida que causava burnout ou starvation.
*/
static void	get_dongle_order(t_coder *coder, int *first, int *second)
{
	int	left;
	int	right;

	left = coder->left_dongle;
	right = coder->right_dongle;
	pthread_mutex_lock(&coder->sim->dongle_order_mutex);
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
	pthread_mutex_unlock(&coder->sim->dongle_order_mutex);
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
	coder->state = STATE_WAITING;
	dongle_release(&sim->dongles[second], coder);
	dongle_release(&sim->dongles[first], coder);
	return (1);
}

static int	do_debug(t_coder *coder)
{
	t_sim	*sim;

	sim = coder->sim;
	if (sim_is_stopped(sim))
		return (0);
	coder->state = STATE_DEBUGGING;
	log_state(sim, coder->id, "is debugging");
	sleep_ms(sim->time_to_debug);
	return (1);
}

static int	do_refactor(t_coder *coder)
{
	t_sim	*sim;

	sim = coder->sim;
	if (sim_is_stopped(sim))
		return (0);
	coder->state = STATE_REFACTORING;
	log_state(sim, coder->id, "is refactoring");
	sleep_ms(sim->time_to_refactor);
	return (1);
}

void	*coder_routine(void *arg)
{
	t_coder	*coder;

	coder = (t_coder *)arg;
	coder->state = STATE_WAITING;
	sleep_ms((long long)(coder->id - 1) * CODER_START_OFFSET);
	while (!sim_is_stopped(coder->sim))
	{
		coder->state = STATE_WAITING;
		if (!do_compile(coder))
			break ;
		if (!do_debug(coder))
			break ;
		if (!do_refactor(coder))
			break ;
	}
	return (NULL);
}
