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

/*
** Returns 1 if this coder is the top of the queue (i.e., has priority)
*/
static int	is_my_turn(t_dongle *d, int coder_id)
{
	t_pq_node	top;

	if (!pq_peek(&d->waiters, &top))
		return (0);
	return (top.coder_id == coder_id);
}

/*
** Acquire a dongle:
**   1. Register in the priority queue with the appropriate key
**   2. Wait until:
**      a. We are at the front of the queue
**      b. The dongle is not in use
**      c. Cooldown has elapsed
**      d. Simulation is not stopped
**   3. Mark dongle as in_use and remove from queue
*/
int	dongle_acquire(t_dongle *d, t_coder *coder)
{
	t_sim		*sim;
	long long	key;
	long long	now;
	long long	wait_ms;

	sim = d->sim;
	pthread_mutex_lock(&d->mutex);

	/* Compute scheduling key */
	if (sim->scheduler == SCHED_FIFO_MODE)
		key = get_time_ms(); /* arrival time */
	else
		key = coder->deadline; /* EDF: earliest deadline first */

	pq_push(&d->waiters, key, coder->id);

	while (1)
	{
		/* Check if sim stopped */
		pthread_mutex_lock(&sim->stop_mutex);
		if (sim->stopped)
		{
			pthread_mutex_unlock(&sim->stop_mutex);
			pq_remove(&d->waiters, coder->id);
			pthread_mutex_unlock(&d->mutex);
			return (0);
		}
		pthread_mutex_unlock(&sim->stop_mutex);

		/* Check if it's our turn and dongle is free */
		if (is_my_turn(d, coder->id) && !d->in_use)
		{
			/* Check cooldown */
			if (d->in_cooldown)
			{
				now = get_time_ms();
				wait_ms = (d->release_time + sim->dongle_cooldown) - now;
				if (wait_ms <= 0)
					d->in_cooldown = 0;
			}
			if (!d->in_cooldown)
			{
				/* Acquire */
				d->in_use = 1;
				pq_remove(&d->waiters, coder->id);
				pthread_mutex_unlock(&d->mutex);
				return (1);
			}
		}
		/* Wait for a signal (with short timeout to handle cooldown expiry) */
		{
			struct timespec	ts;
			struct timeval	tv;

			gettimeofday(&tv, NULL);
			/* Wake up every 1ms to re-check cooldowns and stop flag */
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
	pthread_mutex_lock(&d->mutex);
	d->in_use = 0;
	d->in_cooldown = 1;
	d->release_time = get_time_ms();
	pthread_cond_broadcast(&d->cond);
	pthread_mutex_unlock(&d->mutex);
}
