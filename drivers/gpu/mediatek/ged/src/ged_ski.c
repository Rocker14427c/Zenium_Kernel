// SPDX-License-Identifier: GPL-2.0
/*
 * GPU sysfs backend — table-driven, add nodes by editing gpu_nodes[]
 */

#include <mt-plat/mtk_gpu_utility.h>
#include <mtk_gpufreq.h>
#include "ged_ski.h"

static struct kobject *gpu_kobj;

/*
 * ── node table ───────────────────────────────────────────────
 * Edit this table to add/remove/rename sysfs nodes under
 * /sys/kernel/gpu/. Each entry creates one file.
 *
 *  { "name",  MODE,  show_fn,  store_fn }
 *    mode 0440 = read-only
 *    mode 0660 = read-write
 *    store_fn = NULL for read-only
 */

struct gpu_node {
	const char *name;
	umode_t mode;
	ssize_t (*show)(struct kobject *, struct kobj_attribute *, char *);
	ssize_t (*store)(struct kobject *, struct kobj_attribute *,
			const char *, size_t);
};

/* ── forward declarations ────────────────────────────────── */

static ssize_t gpu_available_governor_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_busy_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_clock_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_freq_table_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_governor_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_max_freq_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_max_freq_store(struct kobject *kobj,
		struct kobj_attribute *attr, const char *buf, size_t count);
static ssize_t gpu_min_freq_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_min_freq_store(struct kobject *kobj,
		struct kobj_attribute *attr, const char *buf, size_t count);
static ssize_t gpu_model_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);
static ssize_t gpu_temp_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf);

/* ── THE TABLE ───────────────────────────────────────────── */
/* Add/remove lines here. That's it. */

static const struct gpu_node gpu_nodes[] = {
/*	{ "name",        MODE,  show,              store               },*/
	{ "gpu_available_governor", 0440, gpu_available_governor_show, NULL },
	{ "gpu_busy",          0440, gpu_busy_show,       NULL                },
	{ "gpu_clock",         0440, gpu_clock_show,      NULL            },
	{ "gpu_freq_table",    0440, gpu_freq_table_show, NULL                },
	{ "gpu_governor",      0440, gpu_governor_show,NULL               },
	{ "governor",      0440, gpu_governor_show,   NULL                },
	{ "gpu_max_clock",      0660, gpu_max_freq_show,   gpu_max_freq_store  },
	{ "gpu_min_clock",      0660, gpu_min_freq_show,   gpu_min_freq_store  },
	{ "max_freq",      0660, gpu_max_freq_show,   gpu_max_freq_store  },
	{ "min_freq",      0660, gpu_min_freq_show,   gpu_min_freq_store  },
	{ "gpu_model",         0440, gpu_model_show,      NULL                },
	{ "gpu_tmu",          0440, gpu_temp_show,        NULL               },
};

/* ── dynamic attr storage ────────────────────────────────── */

static struct kobj_attribute gpu_attrs[ARRAY_SIZE(gpu_nodes)];

/* ── show / store functions ──────────────────────────────── */

static ssize_t gpu_available_governor_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	return scnprintf(buf, PAGE_SIZE, "Default\n");
}

static ssize_t gpu_busy_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	unsigned int gpu_loading = 0;

	mtk_get_gpu_loading(&gpu_loading);

	return scnprintf(buf, PAGE_SIZE, "%u\n", gpu_loading);
}

static ssize_t gpu_clock_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	unsigned int gpu_freq = 0;

	gpu_freq = mt_gpufreq_get_freq_by_idx(
			mt_gpufreq_get_cur_freq_index());

	return scnprintf(buf, PAGE_SIZE, "%u\n", gpu_freq / 1000);
}

static ssize_t gpu_freq_table_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	struct mt_gpufreq_power_table_info *power_table = NULL;
	unsigned int table_num = 0;
	unsigned int max_opp_idx = 0;
	char temp[1024] = {0};
	int idx;
	int count = 0;
	int pos = 0;
	int length;

	power_table = pass_gpu_table_to_eara();
	table_num = mt_gpufreq_get_dvfs_table_num();
	max_opp_idx = mt_gpufreq_get_seg_max_opp_index();

	for (idx = max_opp_idx; count < table_num; count++) {
		length = scnprintf(temp + pos, 1024 - pos, "%u ",
				power_table[idx + count].gpufreq_khz / 1000);
		pos += length;
	}

	return scnprintf(buf, PAGE_SIZE, "%s\n", temp);
}

static ssize_t gpu_governor_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	return scnprintf(buf, PAGE_SIZE, "Default\n");
}

static ssize_t gpu_max_freq_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	unsigned int max_clock = 0;
	unsigned long max_clock_custom = 0;

	max_clock = mt_gpufreq_get_thermal_limit_freq();
	mtk_get_gpu_custom_upbound_freq(&max_clock_custom);
	max_clock = (max_clock_custom < max_clock) ?
			max_clock_custom : max_clock;

	return scnprintf(buf, PAGE_SIZE, "%u\n", max_clock / 1000);
}

static ssize_t gpu_max_freq_store(struct kobject *kobj,
		struct kobj_attribute *attr, const char *buf, size_t count)
{
	int max_freq = 0;
	struct mt_gpufreq_power_table_info *power_table = NULL;
	unsigned int table_num = 0;
	unsigned int max_opp_idx = 0;
	int idx = 0;
	int index_count = 0;
	char acBuffer[GED_SYSFS_MAX_BUFF_SIZE];

	if ((count > 0) && (count < GED_SYSFS_MAX_BUFF_SIZE)) {
		if (scnprintf(acBuffer, GED_SYSFS_MAX_BUFF_SIZE, "%s", buf)) {
			if (kstrtoint(acBuffer, 0, &max_freq) == 0) {
				if (max_freq <= 0)
					return -EINVAL;

				power_table = pass_gpu_table_to_eara();
				table_num = mt_gpufreq_get_dvfs_table_num();
				max_opp_idx = mt_gpufreq_get_seg_max_opp_index();

				for (idx = max_opp_idx; index_count < table_num; index_count++) {
					if (max_freq ==
					    power_table[idx + index_count].gpufreq_khz) {
						mtk_custom_upbound_gpu_freq(index_count);
						return count;
					}
				}

				GED_LOGE("SKI: set max clock failed (%d not support)!\n", max_freq);
			}
		}
	}

	return -EINVAL;
}

static ssize_t gpu_min_freq_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	unsigned long min_clock = 0;
	unsigned long min_clock_custom = 0;

	mtk_get_gpu_bottom_freq(&min_clock);
	mtk_get_gpu_custom_boost_freq(&min_clock_custom);
	min_clock = (min_clock_custom > min_clock) ?
			min_clock_custom : min_clock;

	return scnprintf(buf, PAGE_SIZE, "%lu\n", min_clock / 1000);
}

static ssize_t gpu_min_freq_store(struct kobject *kobj,
		struct kobj_attribute *attr, const char *buf, size_t count)
{
	int min_freq = 0;
	struct mt_gpufreq_power_table_info *power_table = NULL;
	unsigned int table_num = 0;
	unsigned int max_opp_idx = 0;
	int idx = 0;
	int index_count = 0;
	char acBuffer[GED_SYSFS_MAX_BUFF_SIZE];

	if ((count > 0) && (count < GED_SYSFS_MAX_BUFF_SIZE)) {
		if (scnprintf(acBuffer, GED_SYSFS_MAX_BUFF_SIZE, "%s", buf)) {
			if (kstrtoint(acBuffer, 0, &min_freq) == 0) {
				if (min_freq <= 0)
					return -EINVAL;

				power_table = pass_gpu_table_to_eara();
				table_num = mt_gpufreq_get_dvfs_table_num();
				max_opp_idx = mt_gpufreq_get_seg_max_opp_index();

				for (idx = max_opp_idx; index_count < table_num; index_count++) {
					if (min_freq ==
					    power_table[idx + index_count].gpufreq_khz) {
						mtk_custom_boost_gpu_freq(index_count);
						return count;
					}
				}

				GED_LOGE("SKI: set min clock failed (%d not support)!\n", min_freq);
			}
		}
	}

	return -EINVAL;
}

static ssize_t gpu_model_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
#if defined(CONFIG_MACH_MT6768)
	return scnprintf(buf, PAGE_SIZE, "Mali-G52 MC2\n");
#elif defined(CONFIG_MACH_MT6781)
	return scnprintf(buf, PAGE_SIZE, "Mali-G57 MC2\n");
#elif defined(CONFIG_MACH_MT6853)
	return scnprintf(buf, PAGE_SIZE, "Mali-G57 MC3\n");
#elif defined(CONFIG_MACH_MT6877)
	return scnprintf(buf, PAGE_SIZE, "Mali-G68 MC4\n");
#elif defined(CONFIG_MACH_MT6785)
	return scnprintf(buf, PAGE_SIZE, "Mali-G76 MP4\n");
#else
	return scnprintf(buf, PAGE_SIZE, "UNKNOWN\n");
#endif
}

static ssize_t gpu_temp_show(struct kobject *kobj,
		struct kobj_attribute *attr, char *buf)
{
	int temperature;

	temperature = mt_gpufreq_get_gpu_temp();

	return scnprintf(buf, PAGE_SIZE, "%d\n", temperature);
}

/* ── init / exit ─────────────────────────────────────────── */

GED_ERROR ged_ski_init(void)
{
	int ret = GED_OK;
	int i;

	gpu_kobj = kobject_create_and_add("gpu", kernel_kobj);
	if (!gpu_kobj) {
		ret = GED_ERROR_OOM;
		GED_LOGE("ged: failed to create gpu_kobj!\n");
		goto EXIT;
	}

	for (i = 0; i < ARRAY_SIZE(gpu_nodes); i++) {
		memset(&gpu_attrs[i], 0, sizeof(gpu_attrs[i]));
		gpu_attrs[i].attr.name = gpu_nodes[i].name;
		gpu_attrs[i].attr.mode = gpu_nodes[i].mode;
		gpu_attrs[i].show = gpu_nodes[i].show;
		gpu_attrs[i].store = gpu_nodes[i].store;

		if (sysfs_create_file(gpu_kobj, &gpu_attrs[i].attr)) {
			GED_LOGE("ged: failed to create %s!\n", gpu_nodes[i].name);
			ret = GED_ERROR_FAIL;
			goto EXIT;
		}
	}

	return ret;

EXIT:
	ged_ski_exit();
	return ret;
}

void ged_ski_exit(void)
{
	int i;

	if (!gpu_kobj)
		return;

	for (i = 0; i < ARRAY_SIZE(gpu_nodes); i++)
		sysfs_remove_file(gpu_kobj, &gpu_attrs[i].attr);

	kobject_put(gpu_kobj);
	gpu_kobj = NULL;
}
