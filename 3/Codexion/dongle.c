/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:05 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/11 19:47:04 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	dongle_init(t_dongle *d, t_sim *sim)
{
	d->sim = sim;
	d->in_use = 0;
	d->in_cooldown = 0;
	d->release_time = 0;
	if (pthread_mutex_init(&d->mutex, NULL) != 0)
		return (0);
	if (pthread_cond_init(&d->cond, NULL) != 0)
	{
		pthread_mutex_destroy(&d->mutex);
		return (0);
	}
	if (!pq_init(&d->waiters, sim->n_coders + 1))
	{
		pthread_cond_destroy(&d->cond);
		pthread_mutex_destroy(&d->mutex);
		return (0);
	}
	return (1);
}

void	dongle_destroy(t_dongle *d)
{
	pq_free(&d->waiters);
	pthread_cond_destroy(&d->cond);
	pthread_mutex_destroy(&d->mutex);
}

void	dongle_release(t_dongle *d, t_coder *coder)
{
	(void)coder;
	pthread_mutex_lock(&d->mutex);
	d->in_use = 0;
	d->in_cooldown = 1;
	d->release_time = get_time_ms();
	pthread_cond_broadcast(&d->cond);
	pthread_mutex_unlock(&d->mutex);
}

static int	acquire_loop(t_dongle *d, t_coder *coder)
{
	t_sim	*sim;

	sim = d->sim;
	while (1)
	{
		pthread_mutex_lock(&sim->stop_mutex);
		if (sim->stopped)
		{
			pthread_mutex_unlock(&sim->stop_mutex);
			pq_remove(&d->waiters, coder->id);
			pthread_mutex_unlock(&d->mutex);
			return (0);
		}
		pthread_mutex_unlock(&sim->stop_mutex);
		if (try_acquire(d, coder))
		{
			pthread_mutex_unlock(&d->mutex);
			return (1);
		}
		wait_one_ms(d);
	}
}

int	dongle_acquire(t_dongle *d, t_coder *coder)
{
	t_sim		*sim;
	long long	key;

	sim = d->sim;
	pthread_mutex_lock(&d->mutex);
	if (sim->scheduler == SCHED_FIFO_MODE)
		key = get_time_ms();
	else
		key = coder->deadline;
	if (!pq_push(&d->waiters, key, coder->id))
	{
		pthread_mutex_unlock(&d->mutex);
		return (0);
	}
	return (acquire_loop(d, coder));
}
