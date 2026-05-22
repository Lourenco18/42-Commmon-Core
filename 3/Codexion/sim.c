#include "codexion.h"

int	sim_init(t_sim *sim)
{
	int	i;

	sim->stopped = 0;
	sim->start_time_ms = get_time_ms();

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

void	sim_run(t_sim *sim)
{
	int	i;

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
}

void	sim_cleanup(t_sim *sim)
{
	int	i;

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
