/* SPDX-License-Identifier: GPL-2.0 */
/*
 * disp_m4u_host_test.c - execute the ported MT6768 display M4U client on the host.
 *
 * Compiles video/mt6768/dispsys/ddp_m4u.c and video/mt6768/videox/disp_helper.c
 * from the ported tree unchanged and drives the boot-visible sequence that the
 * vendor display path uses to hand the LK framebuffer to M4U.  The M4U side is
 * a recording stub whose allocation semantics mirror m4u.c (mode selection from
 * flags, MVA returned through *pMva, port range rejection).
 *
 * What this proves: the client's control flow, its port/larb table, and the
 * exact arguments it hands to the driver.  What it does not prove: any MMIO
 * semantics, translation correctness, or boot behaviour on the phone - those
 * need hardware.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

#include "ddp_m4u.h"
#include "disp_helper.h"

/* ------------------------------------------------------------------ recorder */
unsigned int host_sg_alloc_calls;
unsigned int host_sg_fail_next;
unsigned long host_ioremap_last_pa, host_ioremap_last_size;
int host_vunmap_calls;
unsigned long host_vunmap_last;

static int checks, check_failed;

static void check(const char *name, int ok, const char *fmt, ...)
	__attribute__((format(printf, 3, 4)));

#include <stdarg.h>
static void check(const char *name, int ok, const char *fmt, ...)
{
	char buf[256];
	va_list ap;

	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	checks++;
	if (!ok)
		check_failed++;
	printf("CHECK %-42s %s | %s\n", name, ok ? "PASS" : "FAIL", buf);
	printf("RESULT check.%s=%s %s\n", name, ok ? "pass" : "fail", buf);
}

/* struct m4u_client_t comes from the real m4u_v2_ext.h - the test must not
 * redefine it, only instantiate one.
 */
static struct m4u_client_t the_client;

/* module_to_m4u_larb() is defined in ddp_m4u.c without a prototype in the
 * vendor ddp_m4u.h, so the test declares it here.
 */
int module_to_m4u_larb(enum DISP_MODULE_ENUM module);

static struct {
	int port;
	m4u_fault_callback_t *fn;
	void *data;
} fault_cbs[16];
static int n_fault_cbs;

static struct m4u_port_config_struct cfg_req[16];
static int n_cfg_req;

struct alloc_req {
	struct m4u_client_t *client;
	int port;
	unsigned long va;
	struct sg_table *sgt;
	unsigned int size, prot, flags;
	unsigned int mva_in, mva_out;
};
static struct alloc_req allocs[8];
static int n_allocs;
static unsigned int fake_mva_next = 0x12340000;
static int fake_alloc_rc;

static struct {
	unsigned int mva, size;
	unsigned long *map_va;
	unsigned int *map_size;
} kmaps[8];
static int n_kmaps;
static int n_create_clients;

/* The five M4U entry points the display client uses (declarations come from the
 * real 2.0/m4u_v2.h / m4u_v2_ext.h, so signatures cannot drift here). */
struct m4u_client_t *m4u_create_client(void)
{
	n_create_clients++;
	return &the_client;
}

int m4u_config_port(struct m4u_port_config_struct *pM4uPort)
{
	if (n_cfg_req < (int)ARRAY_SIZE(cfg_req))
		cfg_req[n_cfg_req] = *pM4uPort;
	n_cfg_req++;
	return 0;
}

int m4u_alloc_mva(struct m4u_client_t *client, M4U_PORT_ID port,
		  unsigned long va, struct sg_table *sg_table,
		  unsigned int size, unsigned int prot, unsigned int flags,
		  unsigned int *pMva)
{
	struct alloc_req *r;

	if (port < M4U_PORT_MIN || port >= M4U_PORT_NR)
		return -22;	/* -EINVAL, as the driver rejects out-of-range */
	if (n_allocs < (int)ARRAY_SIZE(allocs)) {
		r = &allocs[n_allocs];
		r->client = client;
		r->port = port;
		r->va = va;
		r->sgt = sg_table;
		r->size = size;
		r->prot = prot;
		r->flags = flags;
		r->mva_in = pMva ? *pMva : 0;
	}
	if (fake_alloc_rc)
		return fake_alloc_rc;
	/* m4u.c: mode comes from flags - a fixed MVA is only honoured with
	 * M4U_FLAGS_FIX_MVA, a start hint only with M4U_FLAGS_START_FROM.
	 * The display client passes flags = 0, so it gets a free MVA and reads
	 * it back through *pMva.
	 */
	if (flags & M4U_FLAGS_FIX_MVA)
		;		/* honour *pMva as-is */
	else
		*pMva = fake_mva_next;
	if (n_allocs < (int)ARRAY_SIZE(allocs))
		allocs[n_allocs].mva_out = *pMva;
	n_allocs++;
	return 0;
}

int m4u_mva_map_kernel(unsigned int mva, unsigned int size,
		       unsigned long *map_va, unsigned int *map_size)
{
	if (n_kmaps < (int)ARRAY_SIZE(kmaps)) {
		kmaps[n_kmaps].mva = mva;
		kmaps[n_kmaps].size = size;
		kmaps[n_kmaps].map_va = map_va;
		kmaps[n_kmaps].map_size = map_size;
	}
	n_kmaps++;
	*map_va = 0x70000000UL + mva;
	*map_size = size;
	return 0;
}

int m4u_register_fault_callback(int port, m4u_fault_callback_t *fn, void *data)
{
	if (n_fault_cbs < (int)ARRAY_SIZE(fault_cbs)) {
		fault_cbs[n_fault_cbs].port = port;
		fault_cbs[n_fault_cbs].fn = fn;
		fault_cbs[n_fault_cbs].data = data;
	}
	n_fault_cbs++;
	return 0;
}

/* ------------------------------------------------------------------ scenario */
#define FB_PA		0x3FF00000ULL		/* typical MT6768 LK logo start */
#define FB_SIZE		(8u << 20)		/* 1080x1920x4 x3 pages ~ 24MB, use 8MB */

static void poison_stack(unsigned int v)
{
	volatile unsigned int buf[512];
	int i;

	for (i = 0; i < 512; i++)
		buf[i] = v;
	/* keep the frame hot so an uninitialised local would show it */
	for (i = 0; i < 512; i++)
		if (buf[i] != v)
			buf[0] = buf[i];
}

int main(void)
{
	int i, r;
	unsigned long va = 0, kva = 0;
	unsigned long mva = 0;
	unsigned int ksz = 0, mva2 = 0;
	unsigned int expect_ports[4];
	static struct sg_table own_sgt;

	printf("=== display M4U client host test (ported tree, real headers) ===\n");
	printf("sizeof(struct m4u_port_config_struct)=%zu offsetof(Virtuality)=%zu offsetof(domain)=%zu offsetof(Distance)=%zu\n",
	       sizeof(struct m4u_port_config_struct),
	       offsetof(struct m4u_port_config_struct, Virtuality),
	       offsetof(struct m4u_port_config_struct, domain),
	       offsetof(struct m4u_port_config_struct, Distance));

	/* 1. the option that gates the whole M4U path */
	r = disp_helper_get_option(DISP_OPT_USE_M4U);
	check("use_m4u_table_default_is_off", r == 0, "get_option(DISP_OPT_USE_M4U)=%d", r);
	disp_helper_option_init();
	r = disp_helper_get_option(DISP_OPT_USE_M4U);
	check("option_init_turns_m4u_on", r == 1, "after disp_helper_option_init()=%d", r);

	/* 2. module <-> port table against the driver's own port IDs */
	expect_ports[0] = M4U_PORT_DISP_OVL0;
	expect_ports[1] = M4U_PORT_DISP_2L_OVL0_LARB0;
	expect_ports[2] = M4U_PORT_DISP_RDMA0;
	expect_ports[3] = M4U_PORT_DISP_WDMA0;
	check("port_ovl0", module_to_m4u_port(DISP_MODULE_OVL0) == (int)expect_ports[0],
	      "module_to_m4u_port(OVL0)=%d want %u", module_to_m4u_port(DISP_MODULE_OVL0), expect_ports[0]);
	check("port_ovl0_2l", module_to_m4u_port(DISP_MODULE_OVL0_2L) == (int)expect_ports[1],
	      "=%d want %u", module_to_m4u_port(DISP_MODULE_OVL0_2L), expect_ports[1]);
	check("port_rdma0", module_to_m4u_port(DISP_MODULE_RDMA0) == (int)expect_ports[2],
	      "=%d want %u", module_to_m4u_port(DISP_MODULE_RDMA0), expect_ports[2]);
	check("port_wdma0", module_to_m4u_port(DISP_MODULE_WDMA0) == (int)expect_ports[3],
	      "=%d want %u", module_to_m4u_port(DISP_MODULE_WDMA0), expect_ports[3]);
	check("larb_all_zero_on_mt6768", module_to_m4u_larb(DISP_MODULE_OVL0) == 0 &&
	      module_to_m4u_larb(DISP_MODULE_WDMA0) == 0,
	      "larb(OVL0)=%d larb(WDMA0)=%d", module_to_m4u_larb(DISP_MODULE_OVL0),
	      module_to_m4u_larb(DISP_MODULE_WDMA0));
	check("reverse_port_to_module", m4u_port_to_module(expect_ports[2]) == DISP_MODULE_RDMA0,
	      "m4u_port_to_module(RDMA0 port)=%d want %d",
	      m4u_port_to_module(expect_ports[2]), (int)DISP_MODULE_RDMA0);
	check("unknown_module_maps_to_nr", module_to_m4u_port(DISP_MODULE_UNKNOWN) == M4U_PORT_NR,
	      "unknown=%d M4U_PORT_UNKNOWN=%d M4U_PORT_NR=%d",
	      module_to_m4u_port(DISP_MODULE_UNKNOWN), M4U_PORT_UNKNOWN, M4U_PORT_NR);

	/* 3. fault callback registration (disp_m4u_init) */
	n_fault_cbs = 0;
	disp_m4u_init();
	check("fault_cbs_registered_4", n_fault_cbs == 4, "n=%d", n_fault_cbs);
	for (i = 0; i < n_fault_cbs && i < 4; i++)
		printf("RESULT fault_cb[%d].port=%d fn=%s\n", i, fault_cbs[i].port,
		       (void *)fault_cbs[i].fn == (void *)disp_m4u_callback ? "disp_m4u_callback" : "other");
	check("fault_cb_ports_match_table", n_fault_cbs == 4 &&
	      fault_cbs[0].port == (int)expect_ports[0] &&
	      fault_cbs[1].port == (int)expect_ports[1] &&
	      fault_cbs[2].port == (int)expect_ports[2] &&
	      fault_cbs[3].port == (int)expect_ports[3], "see fault_cb lines above");
	check("fault_cb_identity", n_fault_cbs == 4 && (void *)fault_cbs[0].fn == (void *)disp_m4u_callback,
	      "fn==disp_m4u_callback");
	if (n_fault_cbs == 4 && fault_cbs[2].fn)
		check("fault_callback_invokes", fault_cbs[2].fn(expect_ports[2], 0x1234000, NULL) == 0,
		      "disp_m4u_callback(RDMA0 port) returns 0");
	check("fault_callback_unknown_port_safe", disp_m4u_callback(M4U_PORT_UNKNOWN, 0, NULL) == 0,
	      "returns 0, no crash");

	/* 4. port configuration (virtual / non-secure / direction) */
	n_cfg_req = 0;
	poison_stack(0xA5A5A5A5u);
	r = config_display_m4u_port();
	check("config_port_returns_ok", r == 0, "ret=%d", r);
	check("config_port_calls_4", n_cfg_req == 4, "n=%d", n_cfg_req);
	for (i = 0; i < n_cfg_req && i < 4; i++)
		printf("RESULT cfg[%d] ePortID=%d Virtuality=%u Security=%u Distance=%u Direction=%d domain=0x%08x\n",
		       i, cfg_req[i].ePortID, cfg_req[i].Virtuality, cfg_req[i].Security,
		       cfg_req[i].Distance, cfg_req[i].Direction, cfg_req[i].domain);
	check("config_port_virtuality_1", n_cfg_req == 4 && cfg_req[0].Virtuality == 1 &&
	      cfg_req[3].Virtuality == 1, "all four ports requested virtual");
	check("config_port_nonsecure", n_cfg_req == 4 && cfg_req[0].Security == 0,
	      "Security=0");
	check("config_port_distance_direction", n_cfg_req == 4 && cfg_req[0].Distance == 1 &&
	      cfg_req[0].Direction == 0, "Distance=1 Direction=0");
	check("config_port_ids_match_table", n_cfg_req == 4 &&
	      cfg_req[0].ePortID == (int)expect_ports[0] && cfg_req[1].ePortID == (int)expect_ports[1] &&
	      cfg_req[2].ePortID == (int)expect_ports[2] && cfg_req[3].ePortID == (int)expect_ports[3],
	      "OVL0, OVL0_2L, RDMA0, WDMA0 in table order");
	printf("RESULT check.config_port_domain_field_uninitialised=info domain=0x%08x (0xA5A5A5A5 means the vendor client leaves struct m4u_port_config_struct.domain unset; MT6768 M4U derives the domain from the port via m4u_get_domain_by_port(), so it is ignored)\n",
	       n_cfg_req ? cfg_req[0].domain : 0);

	/* 5. the LK framebuffer handover: PA -> sg_table -> m4u_alloc_mva */
	n_create_clients = 0;
	n_allocs = 0;
	fake_mva_next = 0x12340000;
	mva = 0;
	va = 0;
	host_sg_alloc_calls = 0;
	r = disp_hal_allocate_framebuffer(FB_PA, FB_PA + FB_SIZE - 1, &va, &mva);
	check("fb_handover_returns_ok", r == 0, "ret=%d", r);
	check("fb_handover_creates_client", n_create_clients == 1, "m4u_create_client calls=%d", n_create_clients);
	check("fb_handover_one_sg_entry", host_sg_alloc_calls == 1, "sg_alloc_table calls=%d", host_sg_alloc_calls);
	check("fb_handover_alloc_recorded", n_allocs == 1, "n=%d", n_allocs);
	if (n_allocs == 1) {
		struct alloc_req *a = &allocs[0];

		check("fb_alloc_port_ovl0", a->port == (int)expect_ports[0], "port=%d", a->port);
		check("fb_alloc_no_va", a->va == 0, "va=0x%lx", a->va);
		check("fb_alloc_sgt_1ent", a->sgt && a->sgt->nents == 1, "nents=%u",
		      a->sgt ? a->sgt->nents : 0);
		check("fb_alloc_sgt_dma_is_fb_pa", a->sgt && sg_dma_address(a->sgt->sgl) == FB_PA,
		      "sg_dma_address=0x%llx want 0x%llx",
		      a->sgt ? (unsigned long long)sg_dma_address(a->sgt->sgl) : 0ULL,
		      (unsigned long long)FB_PA);
		check("fb_alloc_sgt_len_is_full_range", a->sgt && sg_dma_len(a->sgt->sgl) == FB_SIZE,
		      "len=%u want %u", a->sgt ? sg_dma_len(a->sgt->sgl) : 0, FB_SIZE);
		check("fb_alloc_size_arg", a->size == FB_SIZE, "size=%u", a->size);
		check("fb_alloc_prot_rw", a->prot == (M4U_PROT_READ | M4U_PROT_WRITE),
		      "prot=0x%x (READ|WRITE=0x%x)", a->prot, M4U_PROT_READ | M4U_PROT_WRITE);
		check("fb_alloc_flags_zero", a->flags == 0, "flags=0x%x", a->flags);
		check("fb_alloc_presets_mva_to_pa", a->mva_in == (unsigned int)(FB_PA & 0xffffffffULL),
		      "*pMva in=0x%08x (pa&0xffffffff)", a->mva_in);
		check("fb_alloc_mva_is_returned_not_pa", a->mva_out == 0x12340000u && mva == 0x12340000u,
		      "*pMva out=0x%08lx (flags=0 => free MVA; the vendor's pa pre-set is NOT honoured)",
		      mva);
		check("fb_ioremap_wc_on_full_range", host_ioremap_last_pa == FB_PA &&
		      host_ioremap_last_size == FB_SIZE, "ioremap_wc(0x%lx,0x%lx)",
		      host_ioremap_last_pa, host_ioremap_last_size);
	}

	/* 6. generic per-module allocation + the driver's rejection of garbage */
	r = disp_mva_map_kernel(DISP_MODULE_OVL0, mva, FB_SIZE, &kva, &ksz);
	check("map_kernel_returns_ok", r == 0, "ret=%d", r);
	check("map_kernel_args_passed", n_kmaps == 1 && kmaps[0].mva == mva &&
	      kmaps[0].size == FB_SIZE && kva == 0x70000000UL + mva && ksz == FB_SIZE,
	      "mva=0x%08x size=%u kva=0x%lx ksz=%u", mva, FB_SIZE, kva, ksz);
	n_kmaps = 0;
	r = disp_mva_unmap_kernel(mva, FB_SIZE, kva);
	check("unmap_kernel_page_aligns", r == 0 && host_vunmap_calls == 1 &&
	      host_vunmap_last == (kva & ~0xfffUL), "vunmap(0x%lx) want 0x%lx",
	      host_vunmap_last, kva & ~0xfffUL);

	sg_alloc_table(&own_sgt, 1, GFP_KERNEL);
	own_sgt.sgl->dma_address = 0x30000000ULL;
	own_sgt.sgl->length = 4096;
	i = 0;
	r = disp_allocate_mva(&the_client, DISP_MODULE_WDMA0, 0, &own_sgt, 4096,
			      M4U_PROT_WRITE, 0, (unsigned int *)&i);
	check("alloc_wdma0_via_module", n_allocs == 2 && allocs[1].port == (int)expect_ports[3] &&
	      allocs[1].size == 4096 && allocs[1].prot == M4U_PROT_WRITE,
	      "ret=%d port=%d", r, allocs[1].port);
	r = disp_allocate_mva(&the_client, DISP_MODULE_UNKNOWN, 0, &own_sgt, 4096,
			      M4U_PROT_READ, 0, &mva2);
	check("alloc_unknown_module_short_circuits", r == 1 && n_allocs == 2,
	      "ret=%d (1 == the vendor's error code) allocs still %d", r, n_allocs);

	/* 7. failure path: sg_table allocation error must propagate */
	host_sg_fail_next = 1;
	n_allocs = 0;
	mva = 0;
	r = disp_hal_allocate_framebuffer(FB_PA, FB_PA + FB_SIZE - 1, &va, &mva);
	check("sg_alloc_failure_propagates", r == -12 && n_allocs == 0,
	      "ret=%d allocs=%d", r, n_allocs);

	/* 8. option table round-trip the client relies on */
	check("set_option_by_name_roundtrip",
	      disp_helper_set_option_by_name("DISP_OPT_USE_M4U", 0) == 0 &&
	      disp_helper_get_option(DISP_OPT_USE_M4U) == 0 &&
	      disp_helper_set_option_by_name("DISP_OPT_USE_M4U", 1) == 0 &&
	      disp_helper_get_option(DISP_OPT_USE_M4U) == 1,
	      "DISP_OPT_USE_M4U off/on through the vendor name lookup");
	n_cfg_req = 0;
	r = config_display_m4u_port();
	check("config_port_still_4_when_virtual", n_cfg_req == 4 && r == 0, "n=%d", n_cfg_req);

	printf("=== summary: %d checks, %d failed ===\n", checks, check_failed);
	printf("RESULT checks=%d\nRESULT failed=%d\n", checks, check_failed);
	printf("VERDICT %s\n", check_failed ? "FAIL" : "PASS");
	return check_failed ? 1 : 0;
}
