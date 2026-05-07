#include "codexion.h"

void	log_state(t_sim *sim, int coder_id, const char *msg)
{
	long long	elapsed;

	pthread_mutex_lock(&sim->log_mutex);
	elapsed = get_time_ms() - sim->start_time_ms;
	printf("%lld %d %s\n", elapsed, coder_id, msg);
	pthread_mutex_unlock(&sim->log_mutex);
}
