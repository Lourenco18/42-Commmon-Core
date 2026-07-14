/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   main.c                                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:54 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 14:58:34 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/* 1) Inicia a execução: ler argumentos, inicmulação, correr e limpar. */
int	main(int argc, char **argv)
{
	t_sim	sim;

	memset(&sim, 0, sizeof(t_sim));
	if (!parse_args(argc, argv, &sim))
		return (1);
	if (!sim_init(&sim))
	{
		fprintf(stderr, "Error: failed to initialize simulation\n");
		return (1);
	}
	if (!sim_run(&sim))
	{
		fprintf(stderr, "Error: failed to run simulation\n");
		sim_cleanup(&sim);
		return (1);
	}
	sim_print_stats(&sim);
	sim_cleanup(&sim);
	return (0);
}
