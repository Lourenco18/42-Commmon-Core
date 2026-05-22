/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   log.c                                              :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:51 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:09:47 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/* Escreve evento no log com tempo desde o início da simulação. */
void	log_state(t_sim *sim, int coder_id, const char *msg)
{
	long long	elapsed;

	pthread_mutex_lock(&sim->log_mutex);
	elapsed = get_time_ms() - sim->start_time_ms;
	printf("%lld %d %s\n", elapsed, coder_id, msg);
	pthread_mutex_unlock(&sim->log_mutex);
}
