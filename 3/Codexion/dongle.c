/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:05 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:11:58 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	dongle_init(t_dongle *d, t_sim *sim)
{
	/* 3.1) Criar dongle com fila de espera e sincronização. */
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

static int	is_my_turn(t_dongle *d, int coder_id)
{
	t_pq_node	top;

	if (!pq_peek(&d->waiters, &top))
		return (0);
	return (top.coder_id == coder_id);
}

int	dongle_acquire(t_dongle *d, t_coder *coder)
{
	t_sim		*sim;
	long long	key;
	long long	now;
	long long	wait_ms;

	/* 3.2) Coloca o coder na fila e espera pelo turno e cooldown. */
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

		if (is_my_turn(d, coder->id) && !d->in_use)
		{
			if (d->in_cooldown)
			{
				now = get_time_ms();
				wait_ms = (d->release_time + sim->dongle_cooldown) - now;
				if (wait_ms <= 0)
					d->in_cooldown = 0;
			}
			if (!d->in_cooldown)
			{
				d->in_use = 1;
				pq_remove(&d->waiters, coder->id);
				pthread_mutex_unlock(&d->mutex);
				return (1);
			}
		}
		{
			struct timespec	ts;
			struct timeval	tv;

			gettimeofday(&tv, NULL);
			ts.tv_sec = tv.tv_sec;
			ts.tv_nsec = tv.tv_usec * 1000LL + 1000000LL;
			if (ts.tv_nsec >= 1000000000LL)
			{
				ts.tv_sec++;
				ts.tv_nsec -= 1000000000LL;
			}
			pthread_cond_timedwait(&d->cond, &d->mutex, &ts);
		}
	}
}

void	dongle_release(t_dongle *d, t_coder *coder)
{
	(void)coder;
	/* 3.3) Liberta o dongle e inicia o cooldown antes de avisar a fila. */
	pthread_mutex_lock(&d->mutex);
	d->in_use = 0;
	d->in_cooldown = 1;
	d->release_time = get_time_ms();
	pthread_cond_broadcast(&d->cond);
	pthread_mutex_unlock(&d->mutex);
}
