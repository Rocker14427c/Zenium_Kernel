// SPDX-License-Identifier: GPL-2.0-or-later

#include <linux/kernel.h>
#include <linux/string.h>
#include <linux/err.h>
#include <linux/slab.h>
#include <linux/wait.h>
#include <linux/sched.h>
#include <linux/cpuhotplug.h>
#include <linux/vmalloc.h>
#include <linux/fs.h>

#include "zcomp.h"

#include "backend_lzo.h"
#include "backend_lz4.h"
#include "backend_lz4hc.h"
#include "backend_zstd.h"

static const struct zcomp_ops *backends[] = {
#if IS_ENABLED(CONFIG_ZRAM_BACKEND_LZO)
	&backend_lzo,
#endif
#if IS_ENABLED(CONFIG_ZRAM_BACKEND_LZ4)
	&backend_lz4,
#endif
#if IS_ENABLED(CONFIG_ZRAM_BACKEND_LZ4HC)
	&backend_lz4hc,
#endif
#if IS_ENABLED(CONFIG_ZRAM_BACKEND_ZSTD)
	&backend_zstd,
#endif
	NULL
};

static void zcomp_strm_free(struct zcomp *comp, struct zcomp_strm *zstrm)
{
	comp->ops->destroy_ctx(&zstrm->ctx);
	vfree(zstrm->local_copy);
	vfree(zstrm->buffer);
	zstrm->buffer = NULL;
}

static int zcomp_strm_init(struct zcomp *comp, struct zcomp_strm *zstrm)
{
	int ret;

	ret = comp->ops->create_ctx(comp->params, &zstrm->ctx);
	if (ret)
		return ret;

	zstrm->local_copy = vzalloc(PAGE_SIZE);
	zstrm->buffer = vzalloc(2 * PAGE_SIZE);
	if (!zstrm->buffer || !zstrm->local_copy) {
		zcomp_strm_free(comp, zstrm);
		return -ENOMEM;
	}
	return 0;
}

const struct zcomp_ops *lookup_backend_ops(const char *comp)
{
	int i = 0;

	while (backends[i]) {
		if (sysfs_streq(comp, backends[i]->name))
			break;
		i++;
	}
	return backends[i];
}

bool zcomp_available_algorithm(const char *comp)
{
	return lookup_backend_ops(comp) != NULL;
}

ssize_t zcomp_available_show(const char *comp, char *buf)
{
	ssize_t sz = 0;
	int i;

	for (i = 0; i < ARRAY_SIZE(backends) - 1; i++) {
		if (!strcmp(comp, backends[i]->name)) {
			sz += scnprintf(buf + sz, PAGE_SIZE - sz - 2,
					"[%s] ", backends[i]->name);
		} else {
			sz += scnprintf(buf + sz, PAGE_SIZE - sz - 2,
					"%s ", backends[i]->name);
		}
	}

	sz += scnprintf(buf + sz, PAGE_SIZE - sz, "\n");
	return sz;
}

struct zcomp_strm *zcomp_stream_get(struct zcomp *comp)
{
	for (;;) {
		struct zcomp_strm *zstrm = raw_cpu_ptr(comp->stream);

		mutex_lock(&zstrm->lock);
		if (likely(zstrm->buffer))
			return zstrm;
		mutex_unlock(&zstrm->lock);
	}
}

void zcomp_stream_put(struct zcomp_strm *zstrm)
{
	mutex_unlock(&zstrm->lock);
}

/*
 * Preempt-safe per-CPU stream access for hot paths that may run in
 * atomic context (e.g. the synchronous swapin path, which holds the
 * PTE lock).  Preemption is disabled while the stream is in use, so
 * the stream cannot be contended or freed by CPU hotplug and no
 * sleeping lock is needed.
 */
struct zcomp_strm *zcomp_strm_find(struct zcomp *comp)
{
	return get_cpu_ptr(comp->stream);
}

void zcomp_strm_release(struct zcomp *comp, struct zcomp_strm *zstrm)
{
	put_cpu_ptr(comp->stream);
}

int zcomp_compress(struct zcomp *comp, struct zcomp_strm *zstrm,
		   const void *src, unsigned int *dst_len)
{
	struct zcomp_req req = {
		.src = src,
		.dst = zstrm->buffer,
		.src_len = PAGE_SIZE,
		.dst_len = 2 * PAGE_SIZE,
	};
	int ret;

	might_sleep();
	ret = comp->ops->compress(comp->params, &zstrm->ctx, &req);
	if (!ret)
		*dst_len = req.dst_len;
	return ret;
}

int zcomp_decompress(struct zcomp *comp, struct zcomp_strm *zstrm,
		     const void *src, unsigned int src_len, void *dst)
{
	struct zcomp_req req = {
		.src = src,
		.dst = dst,
		.src_len = src_len,
		.dst_len = PAGE_SIZE,
	};

	/*
	 * No might_sleep() here: the read path acquires the stream with
	 * zcomp_strm_find() (preemption disabled) and may be entered from
	 * the synchronous swap-in fault path.  Decompression backends must
	 * not sleep.
	 */
	return comp->ops->decompress(comp->params, &zstrm->ctx, &req);
}

int zcomp_cpu_up_prepare(unsigned int cpu, struct hlist_node *node)
{
	struct zcomp *comp = hlist_entry(node, struct zcomp, node);
	struct zcomp_strm *zstrm = per_cpu_ptr(comp->stream, cpu);
	int ret;

	ret = zcomp_strm_init(comp, zstrm);
	if (ret)
		pr_err("Can't allocate a compression stream\n");
	return ret;
}

int zcomp_cpu_dead(unsigned int cpu, struct hlist_node *node)
{
	struct zcomp *comp = hlist_entry(node, struct zcomp, node);
	struct zcomp_strm *zstrm = per_cpu_ptr(comp->stream, cpu);

	mutex_lock(&zstrm->lock);
	zcomp_strm_free(comp, zstrm);
	mutex_unlock(&zstrm->lock);
	return 0;
}

static int zcomp_init(struct zcomp *comp, struct zcomp_params *params)
{
	int ret, cpu;

	comp->stream = alloc_percpu(struct zcomp_strm);
	if (!comp->stream)
		return -ENOMEM;

	comp->params = params;
	ret = comp->ops->setup_params(comp->params);
	if (ret)
		goto cleanup;

	for_each_possible_cpu(cpu)
		mutex_init(&per_cpu_ptr(comp->stream, cpu)->lock);

	ret = cpuhp_state_add_instance(CPUHP_ZCOMP_PREPARE, &comp->node);
	if (ret < 0)
		goto cleanup;

	return 0;

cleanup:
	comp->ops->release_params(comp->params);
	free_percpu(comp->stream);
	return ret;
}

void zcomp_destroy(struct zcomp *comp)
{
	cpuhp_state_remove_instance(CPUHP_ZCOMP_PREPARE, &comp->node);
	comp->ops->release_params(comp->params);
	free_percpu(comp->stream);
	vfree(comp->params->dict);
	kfree(comp->params);
	kfree(comp);
}

struct zcomp *zcomp_create(const char *alg, struct zcomp_params *params)
{
	struct zcomp *comp;
	int error;

	BUILD_BUG_ON(ARRAY_SIZE(backends) <= 1);

	comp = kzalloc(sizeof(struct zcomp), GFP_KERNEL);
	if (!comp)
		return ERR_PTR(-ENOMEM);

	comp->ops = lookup_backend_ops(alg);
	if (!comp->ops) {
		kfree(comp);
		return ERR_PTR(-EINVAL);
	}

	if (params) {
		void *orig_dict = params->dict;
		size_t orig_dict_sz = params->dict_sz;

		params = kmemdup(params, sizeof(*params), GFP_KERNEL);
		if (!params) {
			kfree(comp);
			return ERR_PTR(-ENOMEM);
		}
		params->drv_data = NULL;
		if (orig_dict_sz && orig_dict) {
			params->dict = vmalloc(orig_dict_sz);
			if (!params->dict) {
				kfree(params);
				kfree(comp);
				return ERR_PTR(-ENOMEM);
			}
			memcpy(params->dict, orig_dict, orig_dict_sz);
			params->dict_sz = orig_dict_sz;
		} else {
			params->dict = NULL;
			params->dict_sz = 0;
		}
	} else {
		params = kzalloc(sizeof(*params), GFP_KERNEL);
		if (!params) {
			kfree(comp);
			return ERR_PTR(-ENOMEM);
		}
		params->level = ZCOMP_PARAM_NO_LEVEL;
	}

	error = zcomp_init(comp, params);
	if (error) {
		kfree(params);
		kfree(comp);
		return ERR_PTR(error);
	}
	return comp;
}

struct zcomp_params *zcomp_params_get(struct list_head *head, const char *alg)
{
	struct zcomp_algorithm_params *ap;

	list_for_each_entry(ap, head, list) {
		if (sysfs_streq(ap->alg, alg))
			return &ap->params;
	}
	return NULL;
}

static void zcomp_params_free_entry(struct zcomp_algorithm_params *ap)
{
	const struct zcomp_ops *ops;

	ops = lookup_backend_ops(ap->alg);
	if (ops)
		ops->release_params(&ap->params);
	vfree(ap->params.dict);
	ap->params.dict = NULL;
	ap->params.dict_sz = 0;
	kfree(ap->alg);
	kfree(ap);
}

ssize_t zcomp_algorithm_params_show(struct list_head *head, char *buf)
{
	struct zcomp_algorithm_params *ap;
	ssize_t sz = 0;

	list_for_each_entry(ap, head, list) {
		if (ap->params.priority >= 0)
			sz += scnprintf(buf + sz, PAGE_SIZE - sz,
					"%s priority=%d", ap->alg,
					ap->params.priority);
		else
			sz += scnprintf(buf + sz, PAGE_SIZE - sz,
					"%s", ap->alg);
		if (ap->params.level != ZCOMP_PARAM_NO_LEVEL)
			sz += scnprintf(buf + sz, PAGE_SIZE - sz,
					" level=%d", ap->params.level);
		if (ap->params.dict_sz)
			sz += scnprintf(buf + sz, PAGE_SIZE - sz,
					" dict_size=%zu", ap->params.dict_sz);
		sz += scnprintf(buf + sz, PAGE_SIZE - sz, "\n");
	}

	return sz;
}

int zcomp_algorithm_params_store(struct list_head *head, const char *buf,
				 size_t len)
{
	struct zcomp_algorithm_params *ap, *tmp;
	const struct zcomp_ops *ops;
	const char *alg_name;
	const char *dict_path = NULL;
	char *params_buf, *token, *equal;
	void *dict = NULL;
	loff_t file_sz;
	int level = ZCOMP_PARAM_NO_LEVEL;
	int priority = ZCOMP_PARAM_NO_PRIORITY;
	int ret;

	params_buf = kstrndup(buf, len, GFP_KERNEL);
	if (!params_buf)
		return -ENOMEM;

	token = strim(params_buf);
	if (!*token) {
		kfree(params_buf);
		return -EINVAL;
	}

	alg_name = strsep(&token, " ");
	if (!alg_name || !*alg_name) {
		kfree(params_buf);
		return -EINVAL;
	}

	ops = lookup_backend_ops(alg_name);
	if (!ops) {
		kfree(params_buf);
		return -EINVAL;
	}

	while ((token = strsep(&token, " ")) != NULL) {
		if (!*token)
			continue;

		equal = strchr(token, '=');
		if (!equal) {
			kfree(params_buf);
			return -EINVAL;
		}
		*equal = '\0';
		equal++;

		if (!strcmp(token, "dict")) {
			dict_path = equal;
		} else if (!strcmp(token, "level")) {
			int l;

			ret = kstrtoint(equal, 10, &l);
			if (ret) {
				kfree(params_buf);
				return ret;
			}
			level = l;
		} else if (!strcmp(token, "priority")) {
			int p;

			ret = kstrtoint(equal, 10, &p);
			if (ret) {
				kfree(params_buf);
				return ret;
			}
			priority = p;
		} else {
			kfree(params_buf);
			return -EINVAL;
		}
	}
	kfree(params_buf);

	if (dict_path) {
		ret = kernel_read_file_from_path(dict_path, &dict, &file_sz,
						 PAGE_SIZE, READING_POLICY);
		if (ret)
			return ret;
	}

	list_for_each_entry_safe(ap, tmp, head, list) {
		if (sysfs_streq(ap->alg, alg_name)) {
			list_del(&ap->list);
			zcomp_params_free_entry(ap);
		}
	}

	ap = kzalloc(sizeof(*ap), GFP_KERNEL);
	if (!ap) {
		vfree(dict);
		return -ENOMEM;
	}

	ap->alg = kstrdup(alg_name, GFP_KERNEL);
	if (!ap->alg) {
		vfree(dict);
		kfree(ap);
		return -ENOMEM;
	}

	ap->params.dict = dict;
	ap->params.dict_sz = dict ? file_sz : 0;
	ap->params.level = level;
	ap->params.priority = priority;

	ret = ops->setup_params(&ap->params);
	if (ret) {
		zcomp_params_free_entry(ap);
		return ret;
	}

	list_add_tail(&ap->list, head);
	return 0;
}
