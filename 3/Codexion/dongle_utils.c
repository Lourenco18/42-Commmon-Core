/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   dongle_utils.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:05 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/11 19:47:03 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

void	wait_one_ms(t_dongle *d)
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

int	is_my_turn(t_dongle *d, int coder_id)
{
	t_pq_node	top;

	if (!pq_peek(&d->waiters, &top))
		return (0);
	return (top.coder_id == coder_id);
}

int	try_acquire(t_dongle *d, t_coder *coder)
{
	long long	now;

	if (!is_my_turn(d, coder->id) || d->in_use)
		return (0);
	if (d->in_cooldown)
	{
		now = get_time_ms();
		if ((d->release_time + d->sim->dongle_cooldown) - now <= 0)
			d->in_cooldown = 0;
	}
	if (d->in_cooldown)
		return (0);
	d->in_use = 1;
	pq_remove(&d->waiters, coder->id);
	return (1);
}
