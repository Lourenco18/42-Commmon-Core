/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   codexion.h                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:06:02 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:11:58 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef CODEXION_H
# define CODEXION_H

# include <pthread.h>
# include <stdio.h>
# include <stdlib.h>
# include <string.h>
# include <unistd.h>
# include <sys/time.h>

# define SCHED_FIFO_MODE 0
# define SCHED_EDF_MODE  1


# define STATE_WAITING    0
# define STATE_COMPILING  1
# define STATE_DEBUGGING  2
# define STATE_REFACTORING 3
# define STATE_BURNED_OUT 4

/* Estados dos coders para monitorização e tomada de decisão. */

typedef struct s_sim	t_sim;
typedef struct s_dongle	t_dongle;
typedef struct s_coder	t_coder;
typedef struct s_pq_node t_pq_node;
typedef struct s_pqueue	t_pqueue;


struct s_pq_node
{
	long long	key;       
	int			coder_id; 
};


struct s_pqueue
{
	t_pq_node	*nodes;
	int			size;
	int			capacity;
};


struct s_dongle
{
	pthread_mutex_t	mutex;
	pthread_cond_t	cond;
	int				in_use;        
	int				in_cooldown;  
	long long		release_time;  
	t_pqueue		waiters;       
	t_sim			*sim;
};


struct s_coder
{
	int				id;
	int				left_dongle;   
	int				right_dongle;  
	int				compile_count;
	int				state;
	long long		last_compile_start; 
	long long		deadline; 
	pthread_t		thread;
	t_sim			*sim;
};


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

	t_coder			*coders;
	t_dongle		*dongles;

	pthread_t		monitor_thread;

	pthread_mutex_t	stop_mutex;
	int				stopped;

	pthread_mutex_t	log_mutex;


	long long		start_time_ms;
};



int			parse_args(int argc, char **argv, t_sim *sim);

long long	get_time_ms(void);
void		sleep_ms(long long ms);

int			pq_init(t_pqueue *pq, int capacity);
void		pq_free(t_pqueue *pq);
int			pq_push(t_pqueue *pq, long long key, int coder_id);
int			pq_pop(t_pqueue *pq, t_pq_node *out);
int			pq_peek(t_pqueue *pq, t_pq_node *out);
int			pq_remove(t_pqueue *pq, int coder_id);

int			dongle_init(t_dongle *d, t_sim *sim);
void		dongle_destroy(t_dongle *d);
int			dongle_acquire(t_dongle *d, t_coder *coder);
void		dongle_release(t_dongle *d, t_coder *coder);

void		log_state(t_sim *sim, int coder_id, const char *msg);

void		*monitor_routine(void *arg);

void		*coder_routine(void *arg);

int			sim_init(t_sim *sim);
int			sim_run(t_sim *sim);
void		sim_cleanup(t_sim *sim);

#endif
