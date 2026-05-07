#include "codexion.h"

static int	check_burnout(t_sim *sim)
{
	int			i;
	long long	now;
	long long	deadline;

	now = get_time_ms();
	i = 0;
	while (i < sim->n_coders)
	{
		deadline = sim->coders[i].last_compile_start + sim->time_to_burnout;
		if (now >= deadline && sim->coders[i].state != STATE_COMPILING)
		{
			/* This coder burned out */
			log_state(sim, sim->coders[i].id, "burned out");
			return (i + 1); /* return non-zero coder index */
		}
		i++;
	}
	return (0);
}

static int	check_all_done(t_sim *sim)
{
	int	i;

	i = 0;
	while (i < sim->n_coders)
	{
		if (sim->coders[i].compile_count < sim->n_compiles_required)
			return (0);
		i++;
	}
	return (1);
}

void	*monitor_routine(void *arg)
{
	t_sim	*sim;
	int		should_stop;

	sim = (t_sim *)arg;
	while (1)
	{
		usleep(500); /* check every 0.5ms for precision */

		pthread_mutex_lock(&sim->stop_mutex);
		should_stop = sim->stopped;
		pthread_mutex_unlock(&sim->stop_mutex);

		if (should_stop)
			break ;

		/* Check completion */
		if (check_all_done(sim))
		{
			pthread_mutex_lock(&sim->stop_mutex);
			sim->stopped = 1;
			pthread_mutex_unlock(&sim->stop_mutex);
			/* Wake all dongle waiters */
			{
				int	i;
				i = 0;
				while (i < sim->n_coders)
				{
					pthread_mutex_lock(&sim->dongles[i].mutex);
					pthread_cond_broadcast(&sim->dongles[i].cond);
					pthread_mutex_unlock(&sim->dongles[i].mutex);
					i++;
				}
			}
			break ;
		}

		/* Check burnout */
		if (check_burnout(sim))
		{
			pthread_mutex_lock(&sim->stop_mutex);
			sim->stopped = 1;
			pthread_mutex_unlock(&sim->stop_mutex);
			/* Wake all dongle waiters */
			{
				int	i;
				i = 0;
				while (i < sim->n_coders)
				{
					pthread_mutex_lock(&sim->dongles[i].mutex);
					pthread_cond_broadcast(&sim->dongles[i].cond);
					pthread_mutex_unlock(&sim->dongles[i].mutex);
					i++;
				}
			}
			break ;
		}
	}
	return (NULL);
}
