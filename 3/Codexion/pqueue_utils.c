/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   pqueue_utils.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:07:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/07 17:09:53 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

int	comes_before(t_pq_node *a, t_pq_node *b)
{
	if (a->key < b->key)
		return (1);
	if (a->key == b->key && a->coder_id > b->coder_id)
		return (1);
	return (0);
}

static void	swap_nodes(t_pq_node *a, t_pq_node *b)
{
	t_pq_node	tmp;

	tmp = *a;
	*a = *b;
	*b = tmp;
}

void	pq_sift_up(t_pqueue *pq, int i)
{
	int	parent;

	while (i > 0)
	{
		parent = (i - 1) / 2;
		if (pq->nodes[parent].key <= pq->nodes[i].key)
			break ;
		swap_nodes(&pq->nodes[parent], &pq->nodes[i]);
		i = parent;
	}
}

void	pq_sift_down(t_pqueue *pq, int i)
{
	int	left;
	int	right;
	int	smallest;

	while (1)
	{
		left = 2 * i + 1;
		right = 2 * i + 2;
		smallest = i;
		if (left < pq->size
			&& pq->nodes[left].key < pq->nodes[smallest].key)
			smallest = left;
		if (right < pq->size
			&& pq->nodes[right].key < pq->nodes[smallest].key)
			smallest = right;
		if (smallest == i)
			break ;
		swap_nodes(&pq->nodes[i], &pq->nodes[smallest]);
		i = smallest;
	}
}

int	pq_push(t_pqueue *pq, long long key, int coder_id)
{
	t_pq_node	*new_nodes;
	int			new_cap;

	if (pq->size >= pq->capacity)
	{
		new_cap = pq->capacity * 2;
		new_nodes = (t_pq_node *)malloc(sizeof(t_pq_node) * (size_t)new_cap);
		if (!new_nodes)
			return (0);
		memset(new_nodes, 0, sizeof(t_pq_node) * (size_t)new_cap);
		memcpy(new_nodes, pq->nodes, sizeof(t_pq_node) * (size_t)pq->size);
		free(pq->nodes);
		pq->nodes = new_nodes;
		pq->capacity = new_cap;
	}
	pq->nodes[pq->size].key = key;
	pq->nodes[pq->size].coder_id = coder_id;
	pq_sift_up(pq, pq->size);
	pq->size++;
	return (1);
}
