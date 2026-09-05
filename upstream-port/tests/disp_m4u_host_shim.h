/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Host-test prelude for the MT6768 display M4U client.
 *
 * This is NOT a second implementation of anything vendor: it supplies only the
 * handful of kernel primitives the two ported client files use, so that
 * video/mt6768/dispsys/ddp_m4u.c and video/mt6768/videox/disp_helper.c can be
 * compiled and *executed* on the host.  Everything M4U-facing - port IDs,
 * struct m4u_port_config_struct, M4U_PROT_*, M4U_FLAGS_*, the fault-callback
 * types - is taken from the real headers of the ported tree (the fake m4u.h
 * includes m4u_port.h and m4u_v2_ext.h directly), so the client under test is
 * fed the same ABI the driver exposes.  Prototype agreement between client and
 * driver is proven by the kernel build, not here.
 */
#ifndef _DISP_M4U_HOST_SHIM_H
#define _DISP_M4U_HOST_SHIM_H

#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#define scnprintf snprintf

/* kernel structs the real m4u headers embed by value */
struct mutex { int owned; };
struct list_head { struct list_head *next, *prev; };
struct mm_struct;
struct task_struct;

typedef uint64_t dma_addr_t;
typedef uint64_t phys_addr_t;
typedef unsigned int gfp_t;

#define GFP_KERNEL 0u
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define IS_ERR(p) ((long)(p) < -4095L && (long)(p) >= -4096L)
#define IS_ERR_OR_NULL(p) (!(p) || IS_ERR(p))
#define PAGE_SIZE 4096UL
#define PAGE_MASK (~(PAGE_SIZE - 1))

#define pr_info(fmt, ...)  printf("pr_info  " fmt, ##__VA_ARGS__)
#define pr_warn(fmt, ...)  printf("pr_warn  " fmt, ##__VA_ARGS__)
#define pr_err(fmt, ...)   printf("pr_err   " fmt, ##__VA_ARGS__)
#define pr_debug(fmt, ...) do { if (getenv("HOST_TEST_VERBOSE")) \
		printf("pr_dbg   " fmt, ##__VA_ARGS__); } while (0)

/* scatterlist / sg_table: only the fields the client touches */
struct scatterlist {
	unsigned long  offset;
	dma_addr_t     dma_address;
	unsigned int   length;
};
struct sg_table {
	struct scatterlist *sgl;
	unsigned int        nents;
	unsigned int        orig_nents;
};
#define sg_dma_address(s) ((s)->dma_address)
#define sg_dma_len(s)     ((s)->length)

/* Recorder state lives in disp_m4u_host_test.c: the shim is force-included into
 * every TU, so a static definition here would give each TU its own copy and the
 * counters would never be visible from the test.
 */
extern unsigned int host_sg_alloc_calls;
extern unsigned int host_sg_fail_next;		/* one-shot failure injection */

static inline int sg_alloc_table(struct sg_table *table, unsigned int nents,
				 gfp_t gfp)
{
	(void)gfp;
	host_sg_alloc_calls++;
	if (host_sg_fail_next) {
		host_sg_fail_next = 0;
		return -12;	/* -ENOMEM, what the real call returns */
	}
	table->sgl = calloc(nents ? nents : 1, sizeof(struct scatterlist));
	if (!table->sgl)
		return -12;
	table->nents = nents;
	table->orig_nents = nents;
	return 0;
}

/* ioremap_wc / vunmap: the client only needs a cookie it can hand back */
#define SHIM_IOREMAP_BASE 0x5a5a0000UL
extern unsigned long host_ioremap_last_pa, host_ioremap_last_size;
static inline void *host_ioremap_wc(unsigned long pa, unsigned long size)
{
	host_ioremap_last_pa = pa;
	host_ioremap_last_size = size;
	return (void *)(uintptr_t)(SHIM_IOREMAP_BASE + (pa & 0xffffUL));
}
extern int host_vunmap_calls;
extern unsigned long host_vunmap_last;
static inline void host_vunmap(void *p)
{
	host_vunmap_calls++;
	host_vunmap_last = (unsigned long)(uintptr_t)p;
}
#define ioremap_wc(pa, sz) host_ioremap_wc((unsigned long)(pa), (unsigned long)(sz))
#define vunmap(p) host_vunmap(p)

#endif /* _DISP_M4U_HOST_SHIM_H */
