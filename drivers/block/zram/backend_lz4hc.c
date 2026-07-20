// SPDX-License-Identifier: GPL-2.0-or-later

#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>
#include <linux/lz4.h>

#include "backend_lz4hc.h"

struct lz4hc_ctx {
	void *mem;
	LZ4_streamDecode_t dstrm;
	LZ4_streamHC_t cstrm;
};

static void lz4hc_release_params(struct zcomp_params *params)
{
}

static int lz4hc_setup_params(struct zcomp_params *params)
{
	return 0;
}

static int lz4hc_create(struct zcomp_params *params, struct zcomp_ctx *ctx)
{
	struct lz4hc_ctx *zctx;

	zctx = kzalloc(sizeof(*zctx), GFP_KERNEL);
	if (!zctx)
		return -ENOMEM;

	if (!params->dict_sz) {
		zctx->mem = kzalloc(LZ4HC_MEM_COMPRESS, GFP_KERNEL);
		if (!zctx->mem) {
			kfree(zctx);
			return -ENOMEM;
		}
	} else {
		LZ4_initStreamHC(&zctx->cstrm, sizeof(zctx->cstrm));
	}

	ctx->context = zctx;
	return 0;
}

static void lz4hc_destroy(struct zcomp_ctx *ctx)
{
	struct lz4hc_ctx *zctx = ctx->context;

	if (!zctx)
		return;

	kfree(zctx->mem);
	kfree(zctx);
}

static int lz4hc_compress(struct zcomp_params *params, struct zcomp_ctx *ctx,
			  struct zcomp_req *req)
{
	struct lz4hc_ctx *zctx = ctx->context;
	int level = params->level == ZCOMP_PARAM_NO_LEVEL ?
		    LZ4HC_CLEVEL_DEFAULT : params->level;
	int ret;

	if (!params->dict_sz) {
		ret = LZ4_compress_HC((const char *)req->src,
				      (char *)req->dst,
				      req->src_len, req->dst_len, level,
				      zctx->mem);
		if (!ret)
			return -EINVAL;
		req->dst_len = ret;
		return 0;
	}

	LZ4_resetStreamHC_fast(&zctx->cstrm, level);
	LZ4_loadDictHC(&zctx->cstrm, params->dict, params->dict_sz);
	ret = LZ4_compress_HC_continue(&zctx->cstrm, (const char *)req->src,
					(char *)req->dst, req->src_len,
					req->dst_len);
	if (!ret)
		return -EINVAL;
	req->dst_len = ret;
	return 0;
}

static int lz4hc_decompress(struct zcomp_params *params, struct zcomp_ctx *ctx,
			    struct zcomp_req *req)
{
	struct lz4hc_ctx *zctx = ctx->context;
	int ret;

	if (!params->dict_sz) {
		ret = LZ4_decompress_safe((const char *)req->src,
					  (char *)req->dst,
					  req->src_len, req->dst_len);
		if (ret < 0)
			return -EINVAL;
		return 0;
	}

	LZ4_setStreamDecode(&zctx->dstrm, params->dict, params->dict_sz);
	ret = LZ4_decompress_safe_continue(&zctx->dstrm,
					   (const char *)req->src,
					   (char *)req->dst,
					   req->src_len, req->dst_len);
	if (ret < 0)
		return -EINVAL;
	return 0;
}

const struct zcomp_ops backend_lz4hc = {
	.compress	= lz4hc_compress,
	.decompress	= lz4hc_decompress,
	.create_ctx	= lz4hc_create,
	.destroy_ctx	= lz4hc_destroy,
	.setup_params	= lz4hc_setup_params,
	.release_params	= lz4hc_release_params,
	.name		= "lz4hc",
};
