/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   time_utils.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/05/22 12:07:13 by dasantos          #+#    #+#             */
/*   Updated: 2026/05/22 12:08:17 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/* 1) Obtém o tempo atual em milissegundos. */
long long	get_time_ms(void)
{
	struct timeval	tv;

	/* 2) Lê o tempo do sistema e converte segundos+micros em ms. */
	gettimeofday(&tv, NULL);
	return ((long long)tv.tv_sec * 1000LL + (long long)tv.tv_usec / 1000LL);
}

/* 3) Pausa o processo pelo número de milissegundos pedido. */
void	sleep_ms(long long ms)
{
	if (ms > 0)
		usleep((useconds_t)(ms * 1000));
}
