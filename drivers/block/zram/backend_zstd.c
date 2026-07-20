// SPDX-License-Identifier: GPL-2.0-or-later

#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/vmalloc.h>
#include <linux/zstd.h>

#include "backend_zstd.h"

struct zstd_ctx {
	ZSTD_CCtx *cctx;
	ZSTD_DCtx *dctx;
	void *cctx_workspace;
	void *dctx_workspace;
};

struct zstd_dict {
	ZSTD_CDict *cdict;
	ZSTD_DDict *ddict;
	void *cdict_workspace;
	void *ddict_workspace;
};

static void zstd_release_params(struct zcomp_params *params)
{
	struct zstd_dict *zd = params->drv_data;

	if (!zd)
		return;

	kfree(zd->cdict_workspace);
	kfree(zd->ddict_workspace);
	kfree(zd);
	params->drv_data = NULL;
}

static int zstd_setup_params(struct zcomp_params *params)
{
	ZSTD_parameters zparams;
	struct zstd_dict *zd;
	size_t cdict_size, ddict_size;

	if (params->level == ZCOMP_PARAM_NO_LEVEL)
		params->level = 3;

	if (!params->dict_sz)
		return 0;

	zd = kzalloc(sizeof(*zd), GFP_KERNEL);
	if (!zd)
		return -ENOMEM;

	zparams = ZSTD_getParams(params->level, PAGE_SIZE, params->dict_sz);
	cdict_size = ZSTD_CDictWorkspaceBound(zparams.cParams);
	zd->cdict_workspace = kzalloc(cdict_size, GFP_KERNEL);
	if (!zd->cdict_workspace) {
		kfree(zd);
		return -ENOMEM;
	}

	zd->cdict = ZSTD_initCDict(params->dict, params->dict_sz, zparams,
				   zd->cdict_workspace, cdict_size);
	if (!zd->cdict) {
		kfree(zd->cdict_workspace);
		kfree(zd);
		return -EINVAL;
	}

	ddict_size = ZSTD_DDictWorkspaceBound();
	zd->ddict_workspace = kzalloc(ddict_size, GFP_KERNEL);
	if (!zd->ddict_workspace) {
		kfree(zd->cdict_workspace);
		kfree(zd);
		return -ENOMEM;
	}

	zd->ddict = ZSTD_initDDict(params->dict, params->dict_sz,
				   zd->ddict_workspace, ddict_size);
	if (!zd->ddict) {
		kfree(zd->ddict_workspace);
		kfree(zd->cdict_workspace);
		kfree(zd);
		return -EINVAL;
	}

	params->drv_data = zd;
	return 0;
}

static int zstd_create(struct zcomp_params *params, struct zcomp_ctx *ctx)
{
	struct zstd_ctx *zctx;
	ZSTD_parameters zparams;
	size_t cctx_size, dctx_size;

	zctx = kzalloc(sizeof(*zctx), GFP_KERNEL);
	if (!zctx)
		return -ENOMEM;

	zparams = ZSTD_getParams(params->level, PAGE_SIZE, 0);
	cctx_size = ZSTD_CCtxWorkspaceBound(zparams.cParams);

	zctx->cctx_workspace = kzalloc(cctx_size, GFP_KERNEL);
	if (!zctx->cctx_workspace) {
		kfree(zctx);
		return -ENOMEM;
	}

	zctx->cctx = ZSTD_initCCtx(zctx->cctx_workspace, cctx_size);
	if (!zctx->cctx) {
		kfree(zctx->cctx_workspace);
		kfree(zctx);
		return -EINVAL;
	}

	dctx_size = ZSTD_DCtxWorkspaceBound();
	zctx->dctx_workspace = kzalloc(dctx_size, GFP_KERNEL);
	if (!zctx->dctx_workspace) {
		kfree(zctx->cctx_workspace);
		kfree(zctx);
		return -ENOMEM;
	}

	zctx->dctx = ZSTD_initDCtx(zctx->dctx_workspace, dctx_size);
	if (!zctx->dctx) {
		kfree(zctx->dctx_workspace);
		kfree(zctx->cctx_workspace);
		kfree(zctx);
		return -EINVAL;
	}

	ctx->context = zctx;
	return 0;
}

static void zstd_destroy(struct zcomp_ctx *ctx)
{
	struct zstd_ctx *zctx = ctx->context;

	if (!zctx)
		return;

	kfree(zctx->dctx_workspace);
	kfree(zctx->cctx_workspace);
	kfree(zctx);
}

static int zstd_compress(struct zcomp_params *params, struct zcomp_ctx *ctx,
			 struct zcomp_req *req)
{
	struct zstd_ctx *zctx = ctx->context;
	struct zstd_dict *zd = params->drv_data;
	size_t ret;

	if (!zd) {
		ZSTD_parameters zparams;

		zparams = ZSTD_getParams(params->level, req->src_len,
					 params->dict_sz);
		ret = ZSTD_compressCCtx(zctx->cctx, req->dst, req->dst_len,
					req->src, req->src_len, zparams);
	} else {
		ret = ZSTD_compress_usingCDict(zctx->cctx, req->dst,
					       req->dst_len, req->src,
					       req->src_len, zd->cdict);
	}
	if (ZSTD_isError(ret))
		return -EINVAL;
	req->dst_len = ret;
	return 0;
}

static int zstd_decompress(struct zcomp_params *params, struct zcomp_ctx *ctx,
			   struct zcomp_req *req)
{
	struct zstd_ctx *zctx = ctx->context;
	struct zstd_dict *zd = params->drv_data;
	size_t ret;

	if (!zd) {
		ret = ZSTD_decompressDCtx(zctx->dctx, req->dst, req->dst_len,
					  req->src, req->src_len);
	} else {
		ret = ZSTD_decompress_usingDDict(zctx->dctx, req->dst,
						 req->dst_len, req->src,
						 req->src_len, zd->ddict);
	}
	if (ZSTD_isError(ret))
		return -EINVAL;
	return 0;
}

const struct zcomp_ops backend_zstd = {
	.compress	= zstd_compress,
	.decompress	= zstd_decompress,
	.create_ctx	= zstd_create,
	.destroy_ctx	= zstd_destroy,
	.setup_params	= zstd_setup_params,
	.release_params	= zstd_release_params,
	.name		= "zstd",
};
