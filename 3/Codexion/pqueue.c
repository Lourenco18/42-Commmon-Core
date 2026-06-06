/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   pqueue.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:07:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/05 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	pq_init(t_pqueue *pq, int capacity)
{
	pq->nodes = (t_pq_node *)malloc(sizeof(t_pq_node) * (size_t)capacity);
	if (!pq->nodes)
		return (0);
	pq->size = 0;
	pq->capacity = capacity;
	return (1);
}

void	pq_free(t_pqueue *pq)
{
	if (pq->nodes)
	{
		free(pq->nodes);
		pq->nodes = NULL;
	}
	pq->size = 0;
	pq->capacity = 0;
}

int	pq_peek(t_pqueue *pq, t_pq_node *out)
{
	if (pq->size == 0)
		return (0);
	*out = pq->nodes[0];
	return (1);
}

int	pq_pop(t_pqueue *pq, t_pq_node *out)
{
	if (pq->size == 0)
		return (0);
	*out = pq->nodes[0];
	pq->size--;
	if (pq->size > 0)
	{
		pq->nodes[0] = pq->nodes[pq->size];
		pq_sift_down(pq, 0);
	}
	return (1);
}

int	pq_remove(t_pqueue *pq, int coder_id)
{
	int	i;

	i = 0;
	while (i < pq->size)
	{
		if (pq->nodes[i].coder_id == coder_id)
		{
			pq->size--;
			if (i < pq->size)
			{
				pq->nodes[i] = pq->nodes[pq->size];
				pq_sift_down(pq, i);
				pq_sift_up(pq, i);
			}
			return (1);
		}
		i++;
	}
	return (0);
}
