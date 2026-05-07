#include "codexion.h"

static int	is_positive_int(const char *s)
{
	int	i;

	if (!s || !*s)
		return (0);
	i = 0;
	while (s[i])
	{
		if (s[i] < '0' || s[i] > '9')
			return (0);
		i++;
	}
	return (i > 0);
}

int	parse_args(int argc, char **argv, t_sim *sim)
{
	if (argc != 9)
	{
		fprintf(stderr,
			"Usage: %s n_coders time_to_burnout time_to_compile "
			"time_to_debug time_to_refactor n_compiles_required "
			"dongle_cooldown scheduler\n", argv[0]);
		return (0);
	}
	if (!is_positive_int(argv[1]) || !is_positive_int(argv[2])
		|| !is_positive_int(argv[3]) || !is_positive_int(argv[4])
		|| !is_positive_int(argv[5]) || !is_positive_int(argv[6])
		|| !is_positive_int(argv[7]))
	{
		fprintf(stderr, "Error: all numeric arguments must be positive integers\n");
		return (0);
	}
	sim->n_coders = atoi(argv[1]);
	sim->time_to_burnout = (long long)atoi(argv[2]);
	sim->time_to_compile = (long long)atoi(argv[3]);
	sim->time_to_debug = (long long)atoi(argv[4]);
	sim->time_to_refactor = (long long)atoi(argv[5]);
	sim->n_compiles_required = atoi(argv[6]);
	sim->dongle_cooldown = (long long)atoi(argv[7]);
	if (strcmp(argv[8], "fifo") == 0)
		sim->scheduler = SCHED_FIFO_MODE;
	else if (strcmp(argv[8], "edf") == 0)
		sim->scheduler = SCHED_EDF_MODE;
	else
	{
		fprintf(stderr, "Error: scheduler must be 'fifo' or 'edf'\n");
		return (0);
	}
	if (sim->n_coders < 1)
	{
		fprintf(stderr, "Error: number of coders must be at least 1\n");
		return (0);
	}
	return (1);
}
