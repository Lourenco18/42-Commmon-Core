/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   test_tiebreaker.c                                  :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/09 00:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/09 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "test_tiebreaker.h"

static void	push_cases(t_pqueue *pq, t_case *cases, int n)
{
	int	i;

	fprintf(stderr, "  Insert: ");
	i = 0;
	while (i < n)
	{
		fprintf(stderr, "coder%d(dl=%lld) ", cases[i].coder_id,
			cases[i].deadline);
		pq_push(pq, cases[i].deadline, cases[i].coder_id);
		i++;
	}
	fprintf(stderr, "\n");
}

static int	pop_and_check(t_pqueue *pq, t_case *cases, int n)
{
	t_pq_node	out;
	int			i;
	int			ok;

	ok = 1;
	fprintf(stderr, "  Pop order:\n");
	i = 0;
	while (i < n)
	{
		pq_pop(pq, &out);
		fprintf(stderr, "    pos %d -> coder%d (deadline=%lld)",
			i + 1, out.coder_id, out.key);
		if (out.coder_id == cases[i].expected_pos)
			fprintf(stderr, " [PASS]\n");
		else
		{
			fprintf(stderr, " [FAIL] expected coder%d\n",
				cases[i].expected_pos);
			ok = 0;
		}
		i++;
	}
	return (ok);
}

int	run_test(t_case *cases, int n, const char *label)
{
	t_pqueue	pq;
	int			ok;

	fprintf(stderr, "\n%s\n", label);
	pq_init(&pq, n + 1);
	push_cases(&pq, cases, n);
	ok = pop_and_check(&pq, cases, n);
	pq_free(&pq);
	if (ok)
		fprintf(stderr, "  => [PASS]\n");
	else
		fprintf(stderr, "  => [FAIL]\n");
	return (ok);
}
