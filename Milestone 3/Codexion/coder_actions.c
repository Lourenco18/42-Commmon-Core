/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_actions.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/11 00:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/11 19:46:58 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	do_debug(t_coder *coder)
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

int	do_refactor(t_coder *coder)
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
