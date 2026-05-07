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

static void	swap_nodes(t_pq_node *a, t_pq_node *b)
{
	t_pq_node	tmp;

	tmp = *a;
	*a = *b;
	*b = tmp;
}

static void	sift_up(t_pqueue *pq, int i)
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

static void	sift_down(t_pqueue *pq, int i)
{
	int	left;
	int	right;
	int	smallest;

	while (1)
	{
		left = 2 * i + 1;
		right = 2 * i + 2;
		smallest = i;
		if (left < pq->size && pq->nodes[left].key < pq->nodes[smallest].key)
			smallest = left;
		if (right < pq->size && pq->nodes[right].key < pq->nodes[smallest].key)
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
	sift_up(pq, pq->size);
	pq->size++;
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
		sift_down(pq, 0);
	}
	return (1);
}

int	pq_peek(t_pqueue *pq, t_pq_node *out)
{
	if (pq->size == 0)
		return (0);
	*out = pq->nodes[0];
	return (1);
}

/* Remove a specific coder_id from the queue */
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
				sift_down(pq, i);
				sift_up(pq, i);
			}
			return (1);
		}
		i++;
	}
	return (0);
}
