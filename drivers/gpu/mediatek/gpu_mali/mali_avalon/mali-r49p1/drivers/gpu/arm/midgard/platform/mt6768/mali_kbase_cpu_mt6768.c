// SPDX-License-Identifier: GPL-2.0
/*
 * Copyright (c) 2019 MediaTek Inc.
 */

#include <mali_kbase.h>
#include "mali_kbase_cpu_mt6768.h"
#include "mtk_gpufreq.h"

#define CPU_CLOCK_SPEED_UNDEFINED (0)

static u32 cpu_clock_speed = CPU_CLOCK_SPEED_UNDEFINED;

int kbase_get_vexpress_cpu_clock_speed(u32 *cpu_clock)
{
	if (cpu_clock_speed != CPU_CLOCK_SPEED_UNDEFINED) {
		*cpu_clock = cpu_clock_speed;
		return 0;
	}

	*cpu_clock = 0;
	return -EIO;
}

u32 kbase_get_platform_min_freq(void)
{
	return 299000;
}

u32 kbase_get_platform_max_freq(void)
{
	return 1000000;
}

unsigned long kbase_get_platform_gpu_clock_speed(struct kbase_device *kbdev)
{
	unsigned long freq = 0;

#if IS_ENABLED(CONFIG_MTK_GPUFREQ_V2)
	freq = gpufreq_get_cur_freq(TARGET_DEFAULT);
#else
	freq = mt_gpufreq_get_cur_freq();
#endif
	if (freq == 0)
		freq = 823000;

	return freq;
}
