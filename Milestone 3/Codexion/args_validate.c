/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   args_validate.c                                    :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/11 00:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/11 19:46:50 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static int	validate_times(t_sim *sim)
{
	if (sim->time_to_burnout < MIN_TIME_MS
		|| sim->time_to_burnout > MAX_TIME_MS)
		return (fprintf(stderr,
				"Error: time_to_burnout must be [%d, %d] ms\n",
				MIN_TIME_MS, MAX_TIME_MS), 0);
	if (sim->time_to_compile < MIN_TIME_MS
		|| sim->time_to_compile > MAX_TIME_MS)
		return (fprintf(stderr,
				"Error: time_to_compile must be [%d, %d] ms\n",
				MIN_TIME_MS, MAX_TIME_MS), 0);
	if (sim->time_to_debug < MIN_TIME_MS || sim->time_to_debug > MAX_TIME_MS)
		return (fprintf(stderr,
				"Error: time_to_debug must be [%d, %d] ms\n",
				MIN_TIME_MS, MAX_TIME_MS), 0);
	if (sim->time_to_refactor < MIN_TIME_MS
		|| sim->time_to_refactor > MAX_TIME_MS)
		return (fprintf(stderr,
				"Error: time_to_refactor must be [%d, %d] ms\n",
				MIN_TIME_MS, MAX_TIME_MS), 0);
	if (sim->time_to_compile >= sim->time_to_burnout)
		return (fprintf(stderr,
				"Error: time_to_compile must be less than time_to_burnout\n"),
			0);
	return (1);
}

int	validate_limits(t_sim *sim)
{
	if (sim->n_coders < 1 || sim->n_coders > MAX_CODERS)
		return (fprintf(stderr,
				"Error: n_coders must be between 1 and %d\n", MAX_CODERS), 0);
	if (!validate_times(sim))
		return (0);
	if (sim->n_compiles_required < 1
		|| sim->n_compiles_required > MAX_COMPILES)
		return (fprintf(stderr,
				"Error: n_compiles_required must be between 1 and %d\n",
				MAX_COMPILES), 0);
	if (sim->dongle_cooldown < 0 || sim->dongle_cooldown > MAX_TIME_MS)
		return (fprintf(stderr,
				"Error: dongle_cooldown must be [0, %d] ms\n", MAX_TIME_MS),
			0);
	return (1);
}
