#include "codexion.h"

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
	sim_run(&sim);
	sim_cleanup(&sim);
	return (0);
}
