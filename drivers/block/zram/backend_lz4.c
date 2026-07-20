// SPDX-License-Identifier: GPL-2.0-or-later

#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>
#include <linux/lz4.h>

#include "backend_lz4.h"

struct lz4_ctx {
	void *mem;
	LZ4_streamDecode_t dstrm;
	LZ4_stream_t cstrm;
};

static void lz4_release_params(struct zcomp_params *params)
{
}

static int lz4_setup_params(struct zcomp_params *params)
{
	return 0;
}

static int lz4_create(struct zcomp_params *params, struct zcomp_ctx *ctx)
{
	struct lz4_ctx *zctx;

	zctx = kzalloc(sizeof(*zctx), GFP_KERNEL);
	if (!zctx)
		return -ENOMEM;

	if (!params->dict_sz) {
		zctx->mem = kzalloc(LZ4_MEM_COMPRESS, GFP_KERNEL);
		if (!zctx->mem) {
			kfree(zctx);
			return -ENOMEM;
		}
	} else {
		LZ4_initStream(&zctx->cstrm, sizeof(zctx->cstrm));
	}

	ctx->context = zctx;
	return 0;
}

static void lz4_destroy(struct zcomp_ctx *ctx)
{
	struct lz4_ctx *zctx = ctx->context;

	if (!zctx)
		return;

	kfree(zctx->mem);
	kfree(zctx);
}

static int lz4_compress(struct zcomp_params *params, struct zcomp_ctx *ctx,
			struct zcomp_req *req)
{
	struct lz4_ctx *zctx = ctx->context;
	int ret;

	if (!params->dict_sz) {
		ret = LZ4_compress_fast((const char *)req->src,
					(char *)req->dst,
					req->src_len, req->dst_len, 1,
					zctx->mem);
		if (!ret)
			return -EINVAL;
		req->dst_len = ret;
		return 0;
	}

	LZ4_loadDict(&zctx->cstrm, params->dict, params->dict_sz);
	ret = LZ4_compress_fast_continue(&zctx->cstrm, (const char *)req->src,
					 (char *)req->dst, req->src_len,
					 req->dst_len, 1);
	if (!ret)
		return -EINVAL;
	req->dst_len = ret;
	return 0;
}

static int lz4_decompress(struct zcomp_params *params, struct zcomp_ctx *ctx,
			  struct zcomp_req *req)
{
	struct lz4_ctx *zctx = ctx->context;
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

const struct zcomp_ops backend_lz4 = {
	.compress	= lz4_compress,
	.decompress	= lz4_decompress,
	.create_ctx	= lz4_create,
	.destroy_ctx	= lz4_destroy,
	.setup_params	= lz4_setup_params,
	.release_params	= lz4_release_params,
	.name		= "lz4",
};
