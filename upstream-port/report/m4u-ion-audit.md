# M4U <-> ION: measured dependency audit (before any M4U code)

Asked: does the vendor M4U actually need `MTK_ION`, or only its clients do; can 5.15 DMA-BUF/heaps
serve as an equivalent; what is the smallest technically correct path. Everything below is a grep or
a line number in `/home/user/Zenium_Kernel` (4.19.325) or `/home/user/portwork/build` (5.15.220 +
series), not an inference.

## 1. What M4U is on this BSP

`drivers/misc/mediatek/m4u/Makefile` selects the platform dir plus a shared version dir; for MT6768
that means `mt6768/` + `2.0/` (M4U 2.0, printed by the Makefile itself: `$(info M4U version:2.0)`).

| object | source | lines | built by |
|---|---|---|---|
| `m4u_hw.o` | `mt6768/m4u_hw.c` | 3,074 | `obj-$(CONFIG_MTK_M4U)` |
| `m4u.o` | `2.0/m4u.c` | 2,468 | `2.0/Makefile: obj-y` |
| `m4u_mva.o` | `2.0/m4u_mva.c` | 595 | same |
| `m4u_pgtable.o` | `2.0/m4u_pgtable.c` | 1,135 | same |
| `m4u_debug.o` | `2.0/m4u_debug.c` | ~1,100 | same |
| `m4u_sec_gp.o` | `2.0/m4u_sec_gp.c` | - | only with `TRUSTONIC_TEE_SUPPORT`/`MICROTRUST_TEE_SUPPORT` |

Headers: `mt6768/{m4u.h,m4u_hw.h,m4u_platform.h,m4u_port.h,m4u_priv.h,m4u_reg.h,tz_m4u.h}` and
`2.0/{m4u_v2.h,m4u_v2_ext.h,m4u_pgtable.h,m4u_mva.h,m4u_debug.h,m4u_sec_gp.h}`.

## 2. M4U's own ION coupling: one dead function

`ion|ION_IOC|dma_buf|MTK_ION` searched across every file of `mt6768/`: **zero hits**. In `2.0/`:

| file | real ION references |
|---|---|
| `m4u.c` | 0 |
| `m4u_mva.c` | 0 |
| `m4u_pgtable.c` / `.h` | 0 (the two grep hits were `imu_supersection_start(` matching `ion_[a-z_]+\(`) |
| `m4u_debug.c` | 13 lines, all inside one function |

That function is `void m4u_test_ion(void)` (`m4u_debug.c:338-398`): `ion_client_create`,
`ion_alloc(..., ION_HEAP_MULTIMEDIA_MASK, ...)`, `ion_map_kernel`, `ion_kernel_ioctl(ION_CMD_MULTIMEDIA)`,
`ion_phys`, `ion_free`, `ion_client_destroy`. It sits inside `#ifdef CONFIG_M4U_TEST_ION` (line 335,
`#else` at 400 defines `#define m4u_test_ion(...)`), its single call site is `m4u_debug.c:579`, and
`CONFIG_M4U_TEST_ION` has **no Kconfig stanza anywhere in the BSP** and is **absent from
`even_defconfig`** (grep: 0 hits). So on the stock device, M4U compiles with no ION code at all, and
the Kconfig line `MTK_M4U: depends on MTK_ION` is vestigial bookkeeping from when the API took an ION
handle - not a structural requirement.

Why the API needs no allocator: the client entry point is

```c
int m4u_alloc_mva(struct m4u_client_t *client, M4U_PORT_ID port, unsigned long va,
                  struct sg_table *sg_table, unsigned int size, unsigned int prot,
                  unsigned int flags, unsigned int *pMva)          /* 2.0/m4u.c:694 */
```

- if the caller passes a kernel/user `va` without `M4U_FLAGS_SG_READY`, M4U builds the scatterlist
  itself: `m4u_create_sgtable(va, size)` (`:603`, `vmalloc_to_page`/`follow_pte`/`virt_to_page` - all
  present in 5.15), and `m4u_free_mva` puts it;
- if the caller passes an `sg_table` (with `M4U_FLAGS_SG_READY`, checked at `:721`), M4U only maps it.

Either way **no fd, no `struct ion_handle`, no import**: M4U is a pure MVA + pgtable engine over a
caller-supplied buffer. Allocation ownership never enters M4U.

## 3. The clients are where ION actually lives

Call-site census (`m4u_*` by subsystem, all of `drivers/`): video 146, m4u self 63, headers 37, ccu 27,
cameraisp 22, ext_disp 19, `media/platform/mtk-vcodec` 12, pseudo_m4u 11, cmdq 11, vpu 8, mdp 8,
`gpu/drm/mediatek` 4, `staging/android/mtk_ion` 3, iommu 3. `mmlw/` and `cmdq/` call no M4U API directly.

MT6768's display helper (`video/mt6768/dispsys/ddp_m4u.c`) shows the pattern: `#include <ion_priv.h>`,
`disp_ion_create()` wrapping `ion_client_create(g_ion_device, name)`, plus `m4u_config_port`,
`m4u_register_fault_callback`, `m4u_mva_map_kernel`. Kernel-side ION symbol census over
`video/mt6768 + ccu/src + cameraisp/mt6768 + mdp`: `ion_handle` 216, `ion_client` 126, `ion_free` 53,
`ion_kernel_ioctl` 37, `ION_TYPE` 37, `ION_CMD_MULTIMEDIA` 23, `ion_mm_data` 21, `ion_fd` 19,
`ION_LOG_SIZE`/`ION_DECOUPLE_MIRROR_MODE`/`ION_GAINCONTROL_*`/`ION_DIRECT_LINK_MODE`/`ION_PRIMARY`
- i.e. **MTK's extended ION** (`drivers/staging/android/mtk_ion`, `ion_priv.h`, `mtk/ion_drv.h`), not
mainline's plain ION. The clients need that; M4U does not.

## 4. What the 5.15 tree has

| thing | state in `portwork/build` |
|---|---|
| `drivers/staging/android/ion` | **absent** - `drivers/staging/android/` holds only `ashmem.c/h`, `uapi`, Kconfig/Makefile. Mainline ION is not in this base at all, so "keep ION" means transplanting a removed subsystem *plus* MTK's heap extensions |
| `CONFIG_DMABUF_HEAPS` | present in tree (`drivers/dma-buf/heaps/{system_heap.c,cma_heap.c}`), **not set** in this .config |
| `CONFIG_DMA_SHARED_BUFFER` | y |
| `CONFIG_IOMMU_IOVA` | y (mainline `<linux/iova.h>` available; M4U 2.0 uses its own `mvaGraph` allocator in `m4u_mva.c`, not iova) |
| `follow_pte()` | exists (`include/linux/mm.h:1769`) - `m4u_create_sgtable`'s user-VA path compiles |
| `dma_buf_vmap()` | exists in 5.15 (returns `struct ios_map_intr`-free `void *`/`struct dma_buf_map`) |

Client-side equivalence (for the rounds that port clients, *not* for M4U itself):

| BSP client call | 5.15 equivalent | verdict |
|---|---|---|
| `ion_client_create(g_ion_device, name)` | `dma_heap_find("system")` / `_dma_heap_buffer_alloc` | equivalent for plain buffers; `g_ion_device` itself does not exist here |
| `ion_alloc(client, size, align, ION_HEAP_MULTIMEDIA_MASK, flags)` | heap alloc + `heap->ops->allocate` | equivalent, but the *multimedia heap* (MVA booking, contiguous 2 MB CMA-like policy) is an MTK heap, not a mainline one |
| `ion_fd_get(fd)` / `ion_import` then map | `dma_buf_get(fd)` + `dma_buf_attach` + `dma_buf_map_attachment` -> `sg_table` -> `m4u_alloc_mva(..., M4U_FLAGS_SG_READY)` | **exact fit for M4U's API, no M4U change** |
| `ion_map_kernel` | `dma_buf_vmap` | equivalent, minus the cached/uncached choice MTK exposes |
| `ion_phys` | none | not needed by M4U (only the dead self-test used it) |
| `ion_kernel_ioctl(ION_CMD_MULTIMEDIA, ...)` / `ion_mm_data` | none | **no equivalent**: this is where the MTK heap records owner/flags/MVA per buffer. M4U already keeps a parallel record (`struct m4u_buf_info`: va, port, size, prot, flags, sg_table) so the ownership part can live in M4U; the heap-side hooks cannot |
| `ION_LOG_*`, `ION_DECOUPLE_*`, `ION_GAINCONTROL_*`, `ION_DIRECT_LINK_MODE` | none | display compression / secure-decouple / brightness features of MTK's heap: out of scope for M4U, deferred to the display round and left disabled rather than faked |
| userspace `/dev/ion` + `ION_IOC_ALLOC` | `/dev/dma_heap/system`, `ION_IOC_COMPAT` absent | **userspace-visible ABI difference** for any media client round |

## 5. Chosen path (smallest technically correct)

1. **Port M4U with no ION at all.** Keep every file verbatim, including `m4u_debug.c`: the ION block is
   already excluded by the BSP's own `#ifdef CONFIG_M4U_TEST_ION`, which stays undefined exactly as in
   stock. Nothing is deleted, nothing is stubbed - the same preprocessing stock uses.
2. **Replace the Kconfig dependency's justification, not its shape:** `MTK_M4U depends on MTK_SMI_EXT`
   (what it actually calls) and *not* on `MTK_ION`, with this file cited in the help text.
3. **Do not enable `CONFIG_DMABUF_HEAPS` now.** No client is ported, so heaps would bind nothing; the
   same rule that kept `CONFIG_MEDIATEK_SMI`/`MTK_IOMMU` off applies. They get enabled with the first
   client that allocates, and that client converts fd -> `sg_table` and uses `M4U_FLAGS_SG_READY`.
4. **Do not port `drivers/staging/android/mtk_ion`.** Its heap semantics (multimedia mask, `ION_CMD_MULTI-
   MEDIA` booking, LOG/decouple/gain control) are a design decision for the display/video clients, not a
   dependency of the IOMMU engine.
5. Rejected alternatives, kept on record: transplanting all of 4.19 ION to satisfy a vestigial Kconfig
   line; rewriting M4U onto `dma-buf` internally (it never sees a buffer's provenance, so there is
   nothing to rewrite); swapping M4U for mainline `mtk_iommu` (needs `iommus`/`#dma-cells` DT surgery
   that this board's DT does not express, and the 5.15 `mt6779`/`mt6779_data` mismatch noted in
   `hardware-enablement.md`).

## 6. Substrate change this required, already built (build-35)

`CONFIG_MTK_SMI_MT6768` was renamed to **`CONFIG_MTK_SMI_EXT`**, and `drivers/memory/smi_public.h`
(the BSP's 36-line client header, minus its MT6885 sub-include) plus `smi_mm_first_get()` were added.
Reason, measured: `m4u_hw.c:19,1109,1124,2898` and `m4u.c:38` gate their SMI clock keeps on
`#ifdef CONFIG_MTK_SMI_EXT`, and `smi_public.h`'s `#else` branch turns `smi_bus_prepare_enable()` into
`((void)0)` - so any other symbol name would have produced an M4U that compiles and boots with its SMI
clock handling silently removed. `smi_mm_first_get()` is read by `m4u.c` only under
`CONFIG_MACH_MT6765 || CONFIG_MACH_MT6761`, so MT6768 does not depend on its value; it exists so the
declaration in the ported header resolves, returning false because `smi_register()` (its only writer)
is not ported. `smi_debug_bus_hang_detect()` and `smi_sysram_enable()` are declared by that header and
**not defined here**: no M4U path calls them, and their bodies need the GCE/sysram/BWC infrastructure
that is deliberately out; a client that calls one fails to link, which is the intended loud answer.

## 7. What M4U will still need (blockers, measured - input for the port commit)

| dependency | where | count (m4u.c / mva / pgtable / m4u_hw.c / priv.h / reg.h) | plan |
|---|---|---|---|
| `<aee.h>` | `m4u_priv.h:11` | 3 / 3 / 11 / 4 / 7 / 0 | AEE report hooks; provide a 5.15-side shim or drop the calls with a note - to be decided by the actual call sites |
| `<mmprofile.h>`, `<mmprofile_function.h>` | `m4u_priv.h:99-100` | 27 / 4 / 0 / 10 / 7 / 0 | most uses are inside `#ifdef M4U_PROFILE`, which stays undefined (same trick as `CONFIG_M4U_TEST_ION`); the rest are `mmprofile_log_ex` calls to check |
| `<sync_write.h>` | `m4u_reg.h:367`, `m4u.c` | 1 / 0 / 0 / 0 / 0 / 2 | `mtk_sync_write` = ordered `writel` on this SoC; map to `writel` with a comment |
| `-I` list (gud/MobiCore, mach, irq, mmp, smi, 2.0) | `mt6768/Makefile` | - | only the `mmp/` + `smi/` paths are needed once TEE/`M4U_TEE_SERVICE_ENABLE` stay off |
| TEE: `mobicore_driver_api.h`, `tz_m4u.h`, `<linux/sectrace.h>`, `m4u_sec_gp.c` | `m4u.c:45-56`, `:1360-1376` | - | all inside `#ifdef M4U_TEE_SERVICE_ENABLE` / `__M4U_SECURE_SYSTRACE_ENABLE__`, undefined here; `m4u_sec_gp.o` is not built without TEE in stock either |
| `mediatek,m4u` node binding | `m4u_hw.c:2804` (`of_find_compatible_node "mediatek,smi_common"`), `:2830` (`"mediatek,pericfg"`), platform `of_match` | - | bind audit says `mediatek,m4u` nodes=1 `NO_DRIVER` today; the port must show it `ENABLED` against the packaged DTB, the same gate SMI had |
| `MTK_IOMMU_MISC` sibling (`drivers/misc/mediatek/iommu/`) | `m4u_debug.c`/`m4u_secure.c` | - | `depends on MTK_IOMMU_V2` in the BSP and TEE-gated; not part of the M4U minimum |
