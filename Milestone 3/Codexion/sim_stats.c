/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sim_stats.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:07:09 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/05 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

static void	print_compilations(t_sim *sim)
{
	int	i;

	fprintf(stderr, "Compilations:");
	i = 0;
	while (i < sim->n_coders)
	{
		fprintf(stderr, "  coder%d=%d", sim->coders[i].id,
			sim->coders[i].compile_count);
		i++;
	}
	fprintf(stderr, "\n");
}

static void	print_header(t_sim *sim, long long total_ms)
{
	fprintf(stderr, "\n--- Simulation stats ---\n");
	if (sim->burnout_coder_id)
		fprintf(stderr, "Result:        BURNOUT\n");
	else
		fprintf(stderr, "Result:        SUCCESS\n");
	if (sim->scheduler == SCHED_FIFO_MODE)
		fprintf(stderr, "Scheduler:     fifo\n");
	else
		fprintf(stderr, "Scheduler:     edf\n");
	fprintf(stderr, "Total time:    %lldms\n", total_ms);
	fprintf(stderr, "Coders:        %d\n", sim->n_coders);
	fprintf(stderr, "Required:      %d compile(s) each\n",
		sim->n_compiles_required);
}

void	sim_print_stats(t_sim *sim)
{
	long long	total_ms;
	int			total_compiles;
	int			i;

	total_ms = sim->end_time_ms - sim->start_time_ms;
	total_compiles = 0;
	i = 0;
	while (i < sim->n_coders)
	{
		total_compiles += sim->coders[i].compile_count;
		i++;
	}
	print_header(sim, total_ms);
	print_compilations(sim);
	if (sim->burnout_coder_id)
		fprintf(stderr, "Burnout:       coder %d\n", sim->burnout_coder_id);
	else
		fprintf(stderr, "Burnout:       none\n");
	fprintf(stderr, "Total compiles:%d\n", total_compiles);
	fprintf(stderr, "------------------------\n");
}
