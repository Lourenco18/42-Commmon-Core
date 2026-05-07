#ifndef CODEXION_H
# define CODEXION_H

# include <pthread.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>
# include <sys/time.h>

/* ===== SCHEDULER CONSTANTS ===== */
# define SCHED_FIFO_MODE 0
# define SCHED_EDF_MODE  1

/* ===== CODER STATES ===== */
# define STATE_WAITING    0
# define STATE_COMPILING  1
# define STATE_DEBUGGING  2
# define STATE_REFACTORING 3
# define STATE_BURNED_OUT 4

/* ===== FORWARD DECLARATIONS ===== */
typedef struct s_sim	t_sim;
typedef struct s_dongle	t_dongle;
typedef struct s_coder	t_coder;
typedef struct s_pq_node t_pq_node;
typedef struct s_pqueue	t_pqueue;

/* ===== PRIORITY QUEUE NODE ===== */
struct s_pq_node
{
	long long	key;       /* sort key: arrival_time (FIFO) or deadline (EDF) */
	int			coder_id;  /* index into sim->coders */
};

/* ===== PRIORITY QUEUE (MIN-HEAP) ===== */
struct s_pqueue
{
	t_pq_node	*nodes;
	int			size;
	int			capacity;
};

/* ===== DONGLE ===== */
struct s_dongle
{
	pthread_mutex_t	mutex;
	pthread_cond_t	cond;
	int				in_use;        /* 1 if currently held by a coder */
	int				in_cooldown;   /* 1 if in cooldown phase */
	long long		release_time;  /* time dongle was released (ms) */
	t_pqueue		waiters;       /* priority queue of waiting coders */
	t_sim			*sim;
};

/* ===== CODER ===== */
struct s_coder
{
	int				id;
	int				left_dongle;   /* index of left dongle */
	int				right_dongle;  /* index of right dongle */
	int				compile_count;
	int				state;
	long long		last_compile_start; /* time last compile started (ms) */
	long long		deadline;           /* last_compile_start + time_to_burnout */
	pthread_t		thread;
	t_sim			*sim;
};

/* ===== SIMULATION STATE ===== */
struct s_sim
{
	/* Parameters */
	int				n_coders;
	long long		time_to_burnout;
	long long		time_to_compile;
	long long		time_to_debug;
	long long		time_to_refactor;
	int				n_compiles_required;
	long long		dongle_cooldown;
	int				scheduler;

	/* Shared state */
	t_coder			*coders;
	t_dongle		*dongles;

	/* Monitor thread */
	pthread_t		monitor_thread;

	/* Simulation control */
	pthread_mutex_t	stop_mutex;
	int				stopped;         /* 1 when simulation must end */

	/* Log serialization */
	pthread_mutex_t	log_mutex;

	/* Start time */
	long long		start_time_ms;
};

/* ===== FUNCTION PROTOTYPES ===== */

/* args.c */
int			parse_args(int argc, char **argv, t_sim *sim);

/* time_utils.c */
long long	get_time_ms(void);
void		sleep_ms(long long ms);

/* pqueue.c */
int			pq_init(t_pqueue *pq, int capacity);
void		pq_free(t_pqueue *pq);
int			pq_push(t_pqueue *pq, long long key, int coder_id);
int			pq_pop(t_pqueue *pq, t_pq_node *out);
int			pq_peek(t_pqueue *pq, t_pq_node *out);
int			pq_remove(t_pqueue *pq, int coder_id);

/* dongle.c */
int			dongle_init(t_dongle *d, t_sim *sim);
void		dongle_destroy(t_dongle *d);
int			dongle_acquire(t_dongle *d, t_coder *coder);
void		dongle_release(t_dongle *d, t_coder *coder);

/* log.c */
void		log_state(t_sim *sim, int coder_id, const char *msg);

/* monitor.c */
void		*monitor_routine(void *arg);

/* coder.c */
void		*coder_routine(void *arg);

/* sim.c */
int			sim_init(t_sim *sim);
void		sim_run(t_sim *sim);
void		sim_cleanup(t_sim *sim);

#endif
