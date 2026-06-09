/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   test_tiebreaker_main.c                             :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: dasantos <dasantos@student.42porto.com>    +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/09 00:00:00 by dasantos          #+#    #+#             */
/*   Updated: 2026/06/09 00:00:00 by dasantos         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "test_tiebreaker.h"

static int	test1(void)
{
	t_case	c[3];

	c[0].deadline = 1000;
	c[0].coder_id = 1;
	c[0].expected_pos = 3;
	c[1].deadline = 1000;
	c[1].coder_id = 2;
	c[1].expected_pos = 2;
	c[2].deadline = 1000;
	c[2].coder_id = 3;
	c[2].expected_pos = 1;
	return (run_test(c, 3,
			"Test 1: same deadline ids=1,2,3 -> pop order: 3 2 1"));
}

static int	test2(void)
{
	t_case	c[3];

	c[0].deadline = 500;
	c[0].coder_id = 5;
	c[0].expected_pos = 5;
	c[1].deadline = 500;
	c[1].coder_id = 3;
	c[1].expected_pos = 3;
	c[2].deadline = 500;
	c[2].coder_id = 1;
	c[2].expected_pos = 1;
	return (run_test(c, 3,
			"Test 2: same deadline ids=5,3,1 -> pop order: 5 3 1"));
}

static int	test3(void)
{
	t_case	c[4];

	c[0].deadline = 800;
	c[0].coder_id = 3;
	c[0].expected_pos = 5;
	c[1].deadline = 500;
	c[1].coder_id = 2;
	c[1].expected_pos = 2;
	c[2].deadline = 1000;
	c[2].coder_id = 1;
	c[2].expected_pos = 3;
	c[3].deadline = 500;
	c[3].coder_id = 5;
	c[3].expected_pos = 1;
	return (run_test(c, 4,
			"Test 3: mixed+tie dl=800,500,1000,500 -> pop: 5 2 3 1"));
}

static int	test4(void)
{
	t_case	c[3];

	c[0].deadline = 300;
	c[0].coder_id = 1;
	c[0].expected_pos = 3;
	c[1].deadline = 200;
	c[1].coder_id = 2;
	c[1].expected_pos = 2;
	c[2].deadline = 100;
	c[2].coder_id = 3;
	c[2].expected_pos = 1;
	return (run_test(c, 3,
			"Test 4: no tie dl=300,200,100 -> pop: 3 2 1"));
}

int	main(void)
{
	int	all_ok;

	fprintf(stderr, "\n=== EDF Tie-breaker Tests ===\n");
	all_ok = 1;
	all_ok &= test1();
	all_ok &= test2();
	all_ok &= test3();
	all_ok &= test4();
	if (all_ok)
		fprintf(stderr, "\n=== ALL TESTS PASSED ===\n\n");
	else
		fprintf(stderr, "\n=== SOME TESTS FAILED ===\n\n");
	return (!all_ok);
}
