#include "codexion.h"

long long	get_time_ms(void)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	return ((long long)tv.tv_sec * 1000LL + (long long)tv.tv_usec / 1000LL);
}

void	sleep_ms(long long ms)
{
	if (ms > 0)
		usleep((useconds_t)(ms * 1000));
}
