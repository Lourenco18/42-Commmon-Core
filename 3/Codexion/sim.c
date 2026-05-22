/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   sim.c                                              :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:07:09 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:41:11 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/* 2) Inicializar simulação: mutex, coders, dongles e deadlines. */
int	sim_init(t_sim *sim)
{
	int	i;

	sim->stopped = 0;
	sim->burnout_coder_id = 0;
	sim->start_time_ms = get_time_ms();
	sim->end_time_ms = 0;

	if (pthread_mutex_init(&sim->stop_mutex, NULL) != 0)
		return (0);
	if (pthread_mutex_init(&sim->log_mutex, NULL) != 0)
	{
		pthread_mutex_destroy(&sim->stop_mutex);
		return (0);
	}

	sim->coders = (t_coder *)malloc(sizeof(t_coder) * (size_t)sim->n_coders);
	if (!sim->coders)
	{
		pthread_mutex_destroy(&sim->log_mutex);
		pthread_mutex_destroy(&sim->stop_mutex);
		return (0);
	}
	memset(sim->coders, 0, sizeof(t_coder) * (size_t)sim->n_coders);

	sim->dongles = (t_dongle *)malloc(sizeof(t_dongle) * (size_t)sim->n_coders);
	if (!sim->dongles)
	{
		free(sim->coders);
		pthread_mutex_destroy(&sim->log_mutex);
		pthread_mutex_destroy(&sim->stop_mutex);
		return (0);
	}
	memset(sim->dongles, 0, sizeof(t_dongle) * (size_t)sim->n_coders);

	i = 0;
	while (i < sim->n_coders)
	{
		if (!dongle_init(&sim->dongles[i], sim))
		{
			while (--i >= 0)
				dongle_destroy(&sim->dongles[i]);
			free(sim->dongles);
			free(sim->coders);
			pthread_mutex_destroy(&sim->log_mutex);
			pthread_mutex_destroy(&sim->stop_mutex);
			return (0);
		}
		i++;
	}

	i = 0;
	while (i < sim->n_coders)
	{
		sim->coders[i].id = i + 1;
		sim->coders[i].compile_count = 0;
		sim->coders[i].state = STATE_WAITING;
		sim->coders[i].sim = sim;
		sim->coders[i].last_compile_start = sim->start_time_ms;
		sim->coders[i].deadline = sim->start_time_ms + sim->time_to_burnout;
		
		sim->coders[i].left_dongle = i;
		if (sim->n_coders == 1)
			sim->coders[i].right_dongle = 0;
		else
			sim->coders[i].right_dongle = (i + 1) % sim->n_coders;
		i++;
	}
	return (1);
}

int	sim_run(t_sim *sim)
{
	int	i;

	/* 3) Inicia monitor e threads dos coders, espera ambos terminarem. */
	pthread_create(&sim->monitor_thread, NULL, monitor_routine, sim);

	i = 0;
	while (i < sim->n_coders)
	{
		pthread_create(&sim->coders[i].thread, NULL,
			coder_routine, &sim->coders[i]);
		i++;
	}

	i = 0;
	while (i < sim->n_coders)
	{
		pthread_join(sim->coders[i].thread, NULL);
		i++;
	}

	pthread_mutex_lock(&sim->stop_mutex);
	sim->stopped = 1;
	pthread_mutex_unlock(&sim->stop_mutex);

	i = 0;
	while (i < sim->n_coders)
	{
		pthread_mutex_lock(&sim->dongles[i].mutex);
		pthread_cond_broadcast(&sim->dongles[i].cond);
		pthread_mutex_unlock(&sim->dongles[i].mutex);
		i++;
	}

	pthread_join(sim->monitor_thread, NULL);
	return (1);
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
	fprintf(stderr, "\n--- Simulation stats ---\n");
	fprintf(stderr, "Result:        %s\n",
		sim->burnout_coder_id ? "BURNOUT" : "SUCCESS");
	fprintf(stderr, "Scheduler:     %s\n",
		sim->scheduler == SCHED_FIFO_MODE ? "fifo" : "edf");
	fprintf(stderr, "Total time:    %lldms\n", total_ms);
	fprintf(stderr, "Coders:        %d\n", sim->n_coders);
	fprintf(stderr, "Required:      %d compile(s) each\n",
		sim->n_compiles_required);
	fprintf(stderr, "Compilations:");
	i = 0;
	while (i < sim->n_coders)
	{
		fprintf(stderr, "  coder%d=%d", sim->coders[i].id,
			sim->coders[i].compile_count);
		i++;
	}
	fprintf(stderr, "\n");
	if (sim->burnout_coder_id)
		fprintf(stderr, "Burnout:       coder %d\n", sim->burnout_coder_id);
	else
		fprintf(stderr, "Burnout:       none\n");
	fprintf(stderr, "Total compiles:%d\n", total_compiles);
	fprintf(stderr, "------------------------\n");
}

void	sim_cleanup(t_sim *sim)
{
	int	i;

	/* 6) Libertar recursos: dongles, coders e mutexes. */
	i = 0;
	while (i < sim->n_coders)
	{
		dongle_destroy(&sim->dongles[i]);
		i++;
	}
	free(sim->dongles);
	free(sim->coders);
	pthread_mutex_destroy(&sim->log_mutex);
	pthread_mutex_destroy(&sim->stop_mutex);
}
