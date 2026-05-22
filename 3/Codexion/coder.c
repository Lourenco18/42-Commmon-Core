/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder.c                                            :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:05:59 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:09:47 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/* 5) Código do coder: compilar, depurar e refatorar até a simulação parar. */
static int	sim_is_stopped(t_sim *sim)
{
	int	stopped;

	pthread_mutex_lock(&sim->stop_mutex);
	stopped = sim->stopped;
	pthread_mutex_unlock(&sim->stop_mutex);
	return (stopped);
}

static int	do_compile(t_coder *coder)
{
	t_sim	*sim;
	int		left;
	int		right;
	int		first;
	int		second;

	/* 5.1) Tenta adquirir os dois dongles e compilar em série. */

	sim = coder->sim;
	left = coder->left_dongle;
	right = coder->right_dongle;

	if (left < right)
	{
		first = left;
		second = right;
	}
	else
	{
		first = right;
		second = left;
	}

	/* Acquire first dongle */
	if (!dongle_acquire(&sim->dongles[first], coder))
		return (0);
	if (sim_is_stopped(sim))
	{
		dongle_release(&sim->dongles[first], coder);
		return (0);
	}
	log_state(sim, coder->id, "has taken a dongle");

	/* Acquire second dongle */
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

	/* Update deadline and state */
	coder->last_compile_start = get_time_ms();
	coder->deadline = coder->last_compile_start + sim->time_to_burnout;
	coder->state = STATE_COMPILING;
	log_state(sim, coder->id, "is compiling");

	/* Compile */
	sleep_ms(sim->time_to_compile);
	coder->compile_count++;

	/* Release both dongles */
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

	/* deadline already initialized in sim_init */
	coder->state = STATE_WAITING;

	/* 5.2) Ciclo principal do coder: compilar, depurar, refatorar. */
	while (!sim_is_stopped(sim))
	{
		/* Attempt to compile */
		coder->state = STATE_WAITING;
		if (!do_compile(coder))
			break ;
		if (sim_is_stopped(sim))
			break ;

		/* Debug */
		coder->state = STATE_DEBUGGING;
		log_state(sim, coder->id, "is debugging");
		sleep_ms(sim->time_to_debug);
		if (sim_is_stopped(sim))
			break ;

		/* Refactor */
		coder->state = STATE_REFACTORING;
		log_state(sim, coder->id, "is refactoring");
		sleep_ms(sim->time_to_refactor);
	}
	return (NULL);
}
