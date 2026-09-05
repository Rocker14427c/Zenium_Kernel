// SPDX-License-Identifier: GPL-2.0
/*
 * cmdqBackup{Allocate,Read,Write}Slot: does the port behave like stock?
 *
 * The three functions this port supplies in drivers/soc/mediatek/mtk-cmdq-disp-slot.c
 * have no device to exercise them, so what can be settled on a host is settled here:
 * the address arithmetic and the return conventions. "stock" below is transcribed
 * from the vendor tree, function for function -
 *
 *   v3/cmdq_record.c:2004  cmdq_alloc_mem()
 *   v3/cmdq_record.c:2026  cmdq_cpu_read_mem()
 *   v3/cmdq_record.c:2050  cmdq_cpu_write_mem()
 *   v3/cmdq_helper_ext.c:1996  cmdqCoreAllocWriteAddress()   (checks, list add)
 *   v3/cmdq_helper_ext.c:2072  cmdqCoreReadWriteAddress()
 *   v3/cmdq_helper_ext.c:2159  cmdqCoreWriteWriteAddress()
 *
 * and "port" mirrors the file being landed. Both run over ONE shared arena and both
 * use the arena address as the "bus address" (kernel VA == PA here), which is what
 * makes their handles, offsets and list walks directly comparable: the point is to
 * compare logic, not an allocator.
 *
 * Build and run:
 *   cc -O1 -Wall -Wextra -o /tmp/slotcheck \
 *       upstream-port/tests/mtk_disp_slot_host_check.c && /tmp/slotcheck
 * Expect: "N cases, 0 mismatches" (the one intended difference is labelled as such).
 */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint32_t u32;
typedef uint64_t u64;
typedef int32_t s32;
typedef uint64_t dma_addr_t;

#define PAGE_SIZE_T	4096u
#define MAX_SLOTS	(PAGE_SIZE_T / sizeof(u32))	/* cmdq_helper_ext.h:51 */

#define ARENA_BYTES	(64 * 1024)
static unsigned char arena[ARENA_BYTES];
static size_t arena_used;

static void *arena_alloc(size_t n)
{
	void *p;

	n = (n + 63u) & ~63ul;		/* both sides align identically */
	if (arena_used + n > ARENA_BYTES)
		return NULL;
	p = arena + arena_used;
	arena_used += n;
	memset(p, 0, n);
	return p;
}

static dma_addr_t to_bus(void *va) { return (dma_addr_t)(uintptr_t)va; }

struct node {
	struct node *next;
	void *va;
	dma_addr_t pa;
	u32 count;
};

static struct node *stock_list;
static struct node *port_list;

static struct node **headp(bool port)
{
	return port ? &port_list : &stock_list;
}

static void list_add(struct node *n, bool port)
{
	struct node **h = headp(port);

	n->next = *h;
	*h = n;
}

/* ================================================================== STOCK ===== */
static s32 stock_core_alloc(u32 count, dma_addr_t *pa_out)
{
	struct node *n;

	if (!pa_out)
		return -22;

	*pa_out = 0;

	if (!count || count > MAX_SLOTS)
		return -22;

	n = malloc(sizeof(*n));
	if (!n)
		return -12;

	n->count = count;
	n->va = arena_alloc((size_t)count * sizeof(u32));
	if (!n->va) {
		free(n);
		return -12;
	}
	n->pa = to_bus(n->va);
	*pa_out = n->pa;
	list_add(n, false);

	return 0;
}

static u32 stock_core_read(dma_addr_t pa)
{
	struct node *n;
	u32 value = 0;

	if (!pa)
		return 0;

	for (n = stock_list; n; n = n->next) {
		s32 offset = (s32)(pa - n->pa);	/* :2076 - s32, as in stock */

		if (offset >= 0 && (u32)offset / sizeof(u32) < n->count) {
			value = *(u32 *)((char *)n->va + offset);
			break;
		}
	}

	return value;
}

static u32 stock_core_write(dma_addr_t pa, u32 value)
{
	struct node *n;

	if (!pa)
		return 0;

	for (n = stock_list; n; n = n->next) {
		s32 offset = (s32)(pa - n->pa);	/* :2163 - s32, as in stock */

		if (offset >= 0 && (u32)offset / sizeof(u32) < n->count) {
			*(u32 *)((char *)n->va + offset) = value;
			break;
		}
	}

	return value;			/* :2202 - the value, not a status */
}

static s32 stock_alloc_slot(dma_addr_t *h, u32 count)
{
	return stock_core_alloc(count, h);
}

static s32 stock_read_slot(dma_addr_t h, u32 idx, u32 *value)
{
	if (!value)
		return -22;

	*value = stock_core_read(h + (dma_addr_t)idx * sizeof(u32));

	return 0;
}

static s32 stock_write_slot(dma_addr_t h, u32 idx, u32 value)
{
	return (s32)stock_core_write(h + (dma_addr_t)idx * sizeof(u32), value);
}

/* ==================================================================== PORT ==== */
/*
 * Mirrors drivers/soc/mediatek/mtk-cmdq-disp-slot.c: same checks, one global list,
 * same lookup predicate, same index folding, same returns. If that file changes,
 * this side has to change with it - a mismatch here is the whole point.
 */
static s32 port_alloc_slot(dma_addr_t *h, u32 count)
{
	struct node *n;

	if (!h)
		return -22;

	*h = 0;

	if (!count || count > MAX_SLOTS)
		return -22;

	n = malloc(sizeof(*n));
	if (!n)
		return -12;

	n->count = count;
	n->va = arena_alloc((size_t)count * sizeof(u32));
	if (!n->va) {
		free(n);
		return -12;
	}
	n->pa = to_bus(n->va);
	list_add(n, true);
	*h = n->pa;

	return 0;
}

static void *port_lookup(dma_addr_t bus_addr, u32 *off)
{
	struct node *slot;
	long offset;

	for (slot = port_list; slot; slot = slot->next) {
		offset = (long)(bus_addr - slot->pa);	/* long, not s32 - see [6] */
		if (offset >= 0 && (u64)offset / sizeof(u32) < slot->count) {
			*off = (u32)offset;
			return slot->va;
		}
	}

	return NULL;
}

static s32 port_read_slot(dma_addr_t h, u32 idx, u32 *value)
{
	void *va;
	u32 off = 0;

	if (!value)
		return -22;

	*value = 0;
	va = port_lookup(h + (dma_addr_t)idx * sizeof(u32), &off);
	if (va)
		*value = *(u32 *)((char *)va + off);

	return 0;
}

static int port_write_slot(dma_addr_t h, u32 idx, u32 value)
{
	void *va;
	u32 off = 0;

	va = port_lookup(h + (dma_addr_t)idx * sizeof(u32), &off);
	if (va)
		*(u32 *)((char *)va + off) = value;

	return value;
}

/* =================================================================== CASES ==== */
static int cases, mismatches;

static void cmp_rc(const char *what, long a, long b)
{
	cases++;
	printf("  %-54s stock=%-8ld port=%-8ld %s\n", what, a, b,
	       a == b ? "agree" : "MISMATCH");
	if (a != b)
		mismatches++;
}

static void cmp_u32(const char *what, u32 a, u32 b)
{
	cases++;
	printf("  %-54s stock=0x%08x port=0x%08x %s\n", what, a, b,
	       a == b ? "agree" : "MISMATCH");
	if (a != b)
		mismatches++;
}

int main(void)
{
	dma_addr_t sh = 0, ph = 0;
	u32 sv = 0, pv = 0;
	s32 sr = 0, pr = 0;

	printf("cmdqBackup*Slot equivalence: vendor 4.19.325 v3 vs this port\n");
	printf("  MAX_SLOTS=%u   the handle is the bus address of the pool\n\n", (unsigned)MAX_SLOTS);

	printf("[1] allocate: argument validation\n");
	sr = stock_alloc_slot(NULL, 4); pr = port_alloc_slot(NULL, 4);
	cmp_rc("count=4 with a null out-pointer -> rc", sr, pr);
	sh = ph = 0x1111;
	sr = stock_alloc_slot(&sh, 0); pr = port_alloc_slot(&ph, 0);
	cmp_rc("count=0 -> rejected", sr, pr);
	cmp_u32("count=0 leaves the caller's handle zeroed", (u32)sh, (u32)ph);
	sh = ph = 0x1111;
	sr = stock_alloc_slot(&sh, MAX_SLOTS + 1); pr = port_alloc_slot(&ph, MAX_SLOTS + 1);
	cmp_rc("count=MAX_SLOTS+1 -> rejected (stock bound)", sr, pr);
	cmp_u32("...and the handle is zeroed there too", (u32)sh, (u32)ph);
	sr = stock_alloc_slot(&sh, MAX_SLOTS); pr = port_alloc_slot(&ph, MAX_SLOTS);
	cmp_rc("count=MAX_SLOTS -> accepted", sr, pr);

	printf("\n[2] in-range read and write\n");
	sr = stock_alloc_slot(&sh, 4); pr = port_alloc_slot(&ph, 4);
	cmp_rc("allocate 4 slots -> rc", sr, pr);
	for (u32 i = 0; i < 4; i++) {
		sr = stock_write_slot(sh, i, 0xA000 + i);
		pr = port_write_slot(ph, i, 0xA000 + i);
		cmp_rc("write slot i -> returns the VALUE, not a status", sr, pr);
	}
	for (u32 i = 0; i < 4; i++) {
		sv = pv = 0;
		sr = stock_read_slot(sh, i, &sv); pr = port_read_slot(ph, i, &pv);
		cmp_rc("read slot i -> rc", sr, pr);
		cmp_u32("read slot i -> value", sv, pv);
	}
	{
		u32 a[4] = {0}, b[4] = {0};

		for (u32 i = 0; i < 4; i++) {
			stock_read_slot(sh, i, &a[i]);
			port_read_slot(ph, i, &b[i]);
		}
		cases++;
		printf("  %-54s %s\n", "pool holds 0xA000..0xA003 as written",
		       (!memcmp(a, b, sizeof a) && a[0] == 0xA000 && a[3] == 0xA003) ?
		       "agree" : "MISMATCH");
		if (memcmp(a, b, sizeof a) || a[0] != 0xA000 || a[3] != 0xA003)
			mismatches++;
	}

	printf("\n[3] unknown handle, null value pointer, wrapped index\n");
	{
		dma_addr_t bogus = to_bus(arena) + 60 * 1024;

		stock_read_slot(bogus, 0, &sv); port_read_slot(bogus, 0, &pv);
		cmp_u32("read an address no allocation covers -> value 0", sv, pv);
		sr = stock_read_slot(bogus, 0, &sv); pr = port_read_slot(bogus, 0, &pv);
		cmp_rc("read on an unknown handle -> rc still 0 (stock)", sr, pr);
		sr = stock_write_slot(bogus, 0, 0x1234); pr = port_write_slot(bogus, 0, 0x1234);
		cmp_rc("write on an unknown handle -> value, no error", sr, pr);
	}
	sr = stock_read_slot(sh, 0, NULL); pr = port_read_slot(ph, 0, NULL);
	cmp_rc("read with a null value pointer -> -EINVAL", sr, pr);
	sv = pv = 0xA5A5;
	stock_read_slot(sh, 0xFFFFFFFFu, &sv);
	port_read_slot(ph, 0xFFFFFFFFu, &pv);
	cmp_u32("slot_index=0xFFFFFFFF wraps identically", sv, pv);

	printf("\n[4] out-of-range index, and whether anything owns the address\n");
	{
		/*
		 * Index 4 of the first pool is one u32 past its end. The lookup is
		 * range-based over a global list, so the walk does not stop at "not
		 * mine" - it keeps going. Whether that finds a neighbour depends on
		 * where the next pool landed: here it landed 112 bytes further on, so
		 * no allocation owns the stray address and the access is dropped on
		 * both sides. [4b] puts them adjacent to show the other outcome.
		 */
		dma_addr_t s_pool2 = 0, p_pool2 = 0;

		sr = stock_alloc_slot(&s_pool2, 4); pr = port_alloc_slot(&p_pool2, 4);
		cmp_rc("allocate a second 4-slot pool -> rc", sr, pr);
		sv = pv = 0xDEAD;
		/* the pool1 handles came from [2]; reuse them */
		stock_read_slot(sh, 4, &sv); port_read_slot(ph, 4, &pv);
		cmp_u32("read pool1[4]: no owner -> value 0, rc 0", sv, pv);
		stock_write_slot(s_pool2, 0, 0xBEEF);
		port_write_slot(p_pool2, 0, 0xBEEF);
		sv = pv = 0;
		stock_read_slot(s_pool2, 0, &sv); port_read_slot(p_pool2, 0, &pv);
		cmp_u32("the new pool still holds its own value", sv, pv);
		sr = stock_write_slot(sh, 4, 0x5A5A);
		pr = port_write_slot(ph, 4, 0x5A5A);
		cmp_rc("write to an unowned address -> value, no error", sr, pr);
		sv = pv = 0;
		stock_read_slot(s_pool2, 0, &sv); port_read_slot(p_pool2, 0, &pv);
		cmp_u32("...and the new pool was not written through it", sv, pv);
	}

	printf("\n[4b] adjacent pools: a stray index lands in the neighbour, on both sides\n");
	{
		dma_addr_t a1 = 0, a2 = 0, b1 = 0, b2 = 0;
		u32 v1 = 0, v2 = 0;

		/*
		 * 16 slots is exactly one 64-byte arena block, so allocating two of
		 * them back to back per side makes pool2 begin where pool1 ends and
		 * index 16 of pool1 is index 0 of pool2. This is what the range-based
		 * search costs a caller that gets its index wrong, in stock as well as
		 * here; the port keeps it rather than silently diverging, so that a
		 * callsite copied later from a vendor file behaves as it does on 4.19.
		 */
		(void)stock_alloc_slot(&a1, 16);
		(void)stock_alloc_slot(&a2, 16);
		(void)port_alloc_slot(&b1, 16);
		(void)port_alloc_slot(&b2, 16);

		cases++;
		printf("  %-54s stock=%s port=%s %s\n", "each side's two pools are adjacent",
		       a2 == a1 + 64 ? "yes" : "no", b2 == b1 + 64 ? "yes" : "no",
		       (a2 == a1 + 64 && b2 == b1 + 64) ? "agree" : "MISMATCH");
		if (!(a2 == a1 + 64 && b2 == b1 + 64))
			mismatches++;

		stock_write_slot(a2, 0, 0x1111); port_write_slot(b2, 0, 0x1111);
		sr = stock_write_slot(a1, 16, 0xE7E7);
		pr = port_write_slot(b1, 16, 0xE7E7);
		cmp_rc("write pool1[16], one past the end -> the value", sr, pr);
		v1 = v2 = 0;
		stock_read_slot(a2, 0, &v1); port_read_slot(b2, 0, &v2);
		cases++;
		printf("  %-54s stock=0x%08x port=0x%08x %s\n",
		       "pool2[0] was overwritten through pool1[16] (alias)", v1, v2,
		       (v1 == 0xE7E7 && v2 == 0xE7E7) ? "agree, hazard reproduced both sides" : "MISMATCH");
		if (!(v1 == 0xE7E7 && v2 == 0xE7E7))
			mismatches++;
		v1 = v2 = 0;
		stock_read_slot(a1, 16, &v1); port_read_slot(b1, 16, &v2);
		cmp_u32("reading it back via pool1[16] gives the same word", v1, v2);
		v1 = v2 = 0;
		stock_read_slot(a1, 15, &v1); port_read_slot(b1, 15, &v2);
		cmp_u32("in-range pool1[15] was never touched", v1, v2);
	}

	printf("\n[5] the index is scaled by 4 before the search, as in stock\n");
	{
		u32 direct, via = 0;

		stock_write_slot(sh, 2, 0x77);
		port_write_slot(ph, 2, 0x77);
		direct = *(u32 *)((char *)(uintptr_t)sh + 2 * sizeof(u32));
		stock_read_slot(sh, 2, &via);
		cmp_u32("slot 2 is the third u32 of the pool", direct, via);
	}

	printf("\n[6] the one deliberate divergence, demonstrated not argued\n");
	printf("  stock computes the lookup offset as s32 (cmdq_helper_ext.c:2076 and\n"
	       "  :2163); the port uses long. Identical for any two pools within 2 GiB,\n"
	       "  which is the only arrangement this SoC produces (slot buffers come from\n"
	       "  alloc_pages in low DRAM). Two synthetic pools 4 GiB apart:\n");
	{
		static struct node fake;
		struct node *save_s = stock_list, *save_p = port_list;
		dma_addr_t far;
		u32 a_val, b_val = 0, off = 0;
		void *cell, *va;

		cell = arena_alloc(sizeof(u32));
		*(u32 *)cell = 0xC0FFEE;
		fake.va = cell;
		fake.pa = to_bus(cell);
		fake.count = 1;
		fake.next = NULL;
		far = fake.pa + 0x100000000ull;	/* 4 GiB past a 1-slot pool */

		stock_list = &fake;
		port_list = &fake;
		a_val = stock_core_read(far);
		va = port_lookup(far, &off);
		if (va)
			b_val = *(u32 *)((char *)va + off);
		cases++;
		printf("  %-54s stock=0x%08x port=0x%08x %s\n",
		       "read 4 GiB past a 1-slot pool", a_val, b_val,
		       (a_val == 0xC0FFEE && b_val == 0) ?
		       "differs by design (stock truncates to 0 and aliases; port refuses)" :
		       "CHECK");
		if (!(a_val == 0xC0FFEE && b_val == 0))
			mismatches++;
		stock_list = save_s;
		port_list = save_p;
	}

	printf("\n%d cases, %d mismatches\n", cases, mismatches);

	return mismatches ? 1 : 0;
}
