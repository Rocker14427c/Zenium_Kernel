# M4U v2.0 (MT6768) on the 5.15 tree: what landed, what each dependency cost

Round: display/video, M4U port. Patch **0080**, measured on **build-36**, series tree after
`fc7a079a0` (0079). Source of truth for the 4.19 side: `drivers/misc/mediatek/m4u/` in this repo;
the 5.15 side: `/home/user/portwork/build/drivers/misc/mediatek/m4u/`. This is the execution record;
`m4u-ion-audit.md` is the analysis that chose the route, and `KNOWN-ISSUES.md` section 11 keeps the
list of what stayed out.

## 1. What was moved

16 source files, 10,896 lines, copied from the BSP and left byte-identical except where the 5.15
API made an edit unavoidable (section 4) - each such edit is annotated in-file with a
`Port note (5.15)` comment, so `git diff` against the 4.19 tree is the review surface.

| unit | file | lines | state |
|---|---|--:|---|
| MVA allocator | `2.0/m4u_mva.c` (+`.h`) | 595 (+10) | verbatim |
| page tables | `2.0/m4u_pgtable.c` (+`.h`) | 1135 (+197) | verbatim; 1 fops -> `proc_ops` |
| core driver | `2.0/m4u.c` | 2529 | 5 annotations (section 4) |
| debugfs/proc ABI | `2.0/m4u_debug.c` (+`.h`) | 1821 (+15) | 5 fops -> `proc_ops`, `do_mmap` rename |
| common API | `2.0/m4u_v2.h`, `2.0/m4u_v2_ext.h` | 81, 126 | verbatim |
| MT6768 hardware | `mt6768/m4u_hw.c` | 3074 | verbatim (compiled with 1 inherited warning, 5.3) |
| MT6768 headers | `m4u.h`, `m4u_hw.h`, `m4u_platform.h`, `m4u_port.h`, `m4u_priv.h`, `m4u_reg.h` | 11/208/100/85/484/425 | `m4u_priv.h`: 1 macro adapted |
| build glue | `m4u/Kconfig`, `m4u/Makefile`, `2.0/Makefile`, `mt6768/Makefile` | new | modelled on the BSP's, `MTK_ION` dep replaced |
| compat headers | `include/mt-plat/sync_write.h`, `include/mt-plat/mtk_lpae.h` | carried | copied verbatim from the BSP (5.2) |
| tracing API | `mmp/mmprofile.h`, `mmprofile_function.h`, `mmprofile_static_event.h` | carried | headers only, no `mmp/src` (5.4) |

Not moved, on purpose: `2.0/m4u_sec_gp.c`/`.h` and `mt6768/tz_m4u.h` (TEE service, 5.5), and
`drivers/misc/mediatek/mmp/src` (the mmprofile implementation, 5.4).

## 2. Kconfig, and why the dependency is `MTK_SMI_EXT`

```
config MTK_M4U
        bool "MT6768 M4U (multimedia memory management unit)"
        depends on MTK_SMI_EXT
```

The BSP says `depends on MTK_ION`. That line cannot be carried: `grep -rn "config MTK_ION"` over the
5.15 tree returns **nothing**, so keeping it would leave `MTK_M4U` unreachable no matter what else is
enabled - a dead driver, not a missing feature. `MTK_SMI_EXT` is the dependency M4U actually has:
`mt6768/m4u_hw.c` guards its larb clock keeps with `#ifdef CONFIG_MTK_SMI_EXT` (lines 19, 1109,
1124, 2898) and `2.0/m4u.c:39` includes the SMI client header `smi_public.h` under the same symbol,
which is why 0079 renamed the SMI Kconfig to the BSP spelling in the first place. Stock
`even_defconfig` agrees on both names (`CONFIG_MTK_M4U=y:1740`, `CONFIG_MTK_SMI_EXT=y:1810`).

Build wiring follows the BSP layout so no include line had to be rewritten: `drivers/misc/Makefile`
gets `obj-y += mediatek/m4u/`, `drivers/misc/Kconfig` sources the new Kconfig, and `m4u/Makefile`
carries one `subdir-ccflags-y` with the five include directories the vendored `#include` spellings
need (`2.0`, `mt6768`, `mediatek/include`, `mediatek/include/mt-plat`, `mediatek/mmp`,
`drivers/memory`).

## 3. Dependency ledger: predicted blocker -> measured answer

Every item the read of `m4u_priv.h`'s config stack raised, with what it actually cost:

| dependency | where it looked fatal | measured reality | cost |
|---|---|---|---|
| `aee.h` (AEE/KDUMP) | `m4u_priv.h:44` include | zero `aee_*()` calls in any built M4U file; `m4u_aee_err()` (`:58`) is a self-contained `snprintf`+`pr_debug` macro, and `CONFIG_MTK_AEE_FEATURE` is unset in `even_defconfig` | none - include disappears |
| TEE / Trustonic / GenieZone | `tz_m4u.h`, `m4u_sec_gp.c`, `m4u_fb_notifier`, `m4u_gz_sec_init` | `M4U_TEE_SERVICE_ENABLE` needs TRUSTONIC **and** `CONFIG_MTK_TEE_GP_SUPPORT` **and** SEC_VIDEO_PATH/CAM_SECURITY; none exist in the base | none - files not built |
| `mmprofile` (MMP tracing) | `m4u_priv.h:89` `#define M4U_PROFILE` looked unconditional | the *whole* `M4U_PROFILE` surface in `m4u.c` (event array `:75-77`, `m4u_profile_init()` `:112-145`, all 15 trace call sites) and `m4u_v2.h:69-71` are inside `#ifdef M4U_PROFILE`, and the BSP's `mmprofile.h` has its own `!CONFIG_MMPROFILE` branch of `static inline` no-ops ("Put dummy API implementation here") | 3 headers carried, 0 lines of M4U edited |
| `mt-plat/mtk_lpae.h` | `m4u_hw.c:17` | body is entirely inside `#ifdef CONFIG_MTK_LM_MODE` (56 lines, empty for us) | carried verbatim |
| `<sync_write.h>` | `mt6768/m4u_reg.h:367` | `mt_reg_sync_writel(v,a)` = `__raw_writel` + `dsb(sy)`; resolves through the BSP's own `-I .../include/mt-plat` | carried verbatim |
| `smi_public.h` | `m4u.c:39`, `m4u_hw.c:20` | shipped by 0079 at `drivers/memory/smi_public.h` | include path only |
| `CONFIG_FPGA_EARLY_PORTING` | `m4u_hw.c:1467,1517,1526` | unset | none |
| `CONFIG_M4U_TEST_ION` | `m4u_debug.c` ION test block | defined in no Kconfig, unset in `even_defconfig` - stock compiles it out too | none |
| `ion_m4u_client` | `m4u.c:851-919` | an in-kernel shared M4U client (register/alloc/dealloc through M4U's own API), **not** an ION user | kept verbatim |

The audit's prediction that ION was the only real blocker holds; the four items in the "looked
fatal" column above are why the port is 27 files and not a subsystem transplant.

## 4. The 5.15 API drift, one entry per edit

Six edits total. All are "same behaviour, 5.15 spelling"; none is a stub that hides missing work.

1. **`proc_ops` (v5.6 split).** `proc_create*()` takes `const struct proc_ops *` now.
   * `mt6768/m4u_priv.h` `DEFINE_PROC_ATTRIBUTE` now emits `struct proc_ops` (`.proc_open/.proc_read
     /.proc_write/.proc_release/.proc_lseek`), keeping the vendor's `local_inode` copy: 5.15's
     `simple_attr_open()` still reads `inode->i_private` (fs/libfs.c), while `proc_create_data()`
     stores the value in `PDE_DATA()`, so the copy is still the thing that makes the node work.
     Covers all 9 `/proc/m4u_dbg/*` attribute nodes and `/proc/m4u`. Upstream deleted `i_private` in
     6.9 - recorded in KNOWN-ISSUES 11.4 as a rebase marker, not as a bug now.
   * the 6 hand-written `const struct file_operations m4u_proc_*_fops` (5 in `m4u_debug.c`,
     `m4u_proc_pgtable_fops` in `m4u_pgtable.c:1090`) became `struct proc_ops` with the same four
     callbacks. `generic_file_llseek` -> `default_llseek`, which is mainline's choice for proc
     attributes; `simple_attr_*` ignores the position either way.
   * `2.0/m4u.c` gained an `m4u_proc_ops` twin of `m4u_fops` for `/proc/m4u`. `struct proc_ops` has
     `proc_ioctl`/`proc_compat_ioctl`, so the node keeps its ioctls; it has no flush callback, and
     `MTK_M4U_flush()` is a no-op in the vendor driver, so nothing is lost. `m4u_fops` itself stays
     (`__maybe_unused`) for the `!__M4U_USE_PROC_NODE` miscdevice branch.
2. **`platform_driver` lost `.suspend`/`.resume`** - the two fields are dropped from `m4uDrv`.
   `m4u_pm_ops` (`2.0/m4u.c:2342`) already assigns `.suspend/.resume/.freeze/.thaw/.poweroff/
   .restore` to `m4u_pm_suspend/m4u_pm_resume`, which call `m4u_suspend()`/`m4u_resume()`
   (`m4u_reg_backup()`/`m4u_reg_restore()`), and 5.15's `struct dev_pm_ops` still has those members,
   so suspend/hibernate keep the vendor path unchanged. No edit to the pm functions was needed.
3. **`p4d` fold level.** `m4u_user_v2p()`'s walk did `pgd -> pud_offset(pgd, va)`; 5.15 requires
   `p4d_offset(pgd, va)` first. On arm64 p4d is folded, so `p4d_offset()` *is* the pgd - the
   `p4d_none/p4d_bad` test added with it can only fail where `pgd_none/pgd_bad` would have.
4. **`handle_mm_fault()` gained `struct pt_regs *`** (5.15.220) - the one call in
   `m4u_fill_sgtable_user()` passes NULL, i.e. the same "synthetic fault, no register dump".
5. **`do_mmap_pgoff()` -> `do_mmap()`** at the 2 sites in `m4u_debug.c`; this BSP already called it
   with the 8-argument 5.x list, so only the name moved.
6. **`show_pte()` is not available to drivers.** `m4u.c:507/517` called the arm64 helper to dump the
   user PTE when `follow_pte()`/`get_user_pages()` failed; 5.15 made it
   `static void show_pte(unsigned long)` inside `arch/arm64/mm/fault.c` (link error: `undefined
   symbol: show_pte`, the only link failure this round had). The two calls are replaced by a comment
   pointing at `m4u_user_v2p()` directly above them, which reports the exact level that rejected the
   address. Lost: the raw PTE value in the log line. Kept: which level failed, and the error path.

## 5. Compiled out, and what that means for behaviour

**5.1 ION / multimedia allocation ABI.** Unchanged from the audit: M4U itself uses no ION. What the
device-side clients need (`ION_CMD_MULTIMEDIA` heap booking, `ion_mm_data`, `ION_LOG_*`,
`ION_DECOUPLE_*`, `ION_GAINCONTROL_*`, `ion_phys`, `ion_map_kernel`, `/dev/ion`) is still absent -
this build adds no ION and no `CONFIG_DMABUF_HEAPS` (`# CONFIG_DMABUF_HEAPS is not set`), because no
ported client has asked for either yet. M4U's own API is reachable from dma-buf without touching the
driver: `dma_buf_get -> attach -> map_attachment_unlocked` hands over exactly the `sg_table` that
`M4U_FLAGS_SG_READY` expects (`2.0/m4u.c:721`).

**5.2 Vendor compat headers.** `sync_write.h` and `mt-plat/mtk_lpae.h` are carried verbatim under
`drivers/misc/mediatek/include/` rather than folded into the driver, so a later MT6765/MT6761 M4U or
any other `<mt-plat/...>` user resolves them the same way the BSP does.

**5.3 One inherited vendor warning, deliberately not "fixed".** `mt6768/m4u_hw.c:1723` reads
`if ((port_array->ports[port] && M4U_PORT_ATTR_EN) == 0)` - clang says "converting the result of
'<<' to a boolean always evaluates to true" (`-Wtautological-constant-compare`). The intent was
clearly a `&` test of the port's attribute bit; as written, no port is ever skipped by that
condition. This is upstream-visible vendor behaviour in a hardware-programming path, so it is
carried as-is and documented instead of being silently corrected: fixing it changes which M4U ports
get configured. Stock builds the same line.

**5.4 mmprofile tracing.** `M4U_PROFILE` stays defined (vendor spelling), and the three carried
`mmp/*.h` headers resolve it to the vendor's own `!CONFIG_MMPROFILE` no-op inlines. `even_defconfig`
builds the real framework (`CONFIG_MMPROFILE=y:1712`, `CONFIG_MTK_MMPROFILE_SUPPORT=y:1711`), so on
stock the six M4U events (Alloc/DeAlloc MVA, Config Port, M4U ERROR, CACHE_SYNC, Toggle_CG) do
appear in the MMP trace buffer. Here they do not: no `mmp/src`, no `/dev/MMProfile`-side event
registration, and the `M4U_MMP_Events[]` name dump behind `CONFIG_MTK_MMPROFILE` is not built.
Functional impact: M4U's timing/error trace stream is missing; MVA/page-table/port behaviour is not.

**5.5 TEE, secure path, L2.** `m4u_sec_gp.c`, `tz_m4u.h`, `gM4U_L2_enable`, the `m4u_fb_notifier`
secure-region bookkeeping and GenieZone `m4u_gz_sec_init` are all behind
`M4U_TEE_SERVICE_ENABLE`/`M4U_GZ_SERVICE_ENABLE`, which need Trustonic/microtrust +
`CONFIG_MTK_TEE_GP_SUPPORT` + `CONFIG_MTK_SECURE_VIDEO_PATH`/`CAM_SECURITY`. None exists in this
base, so secure display/camera paths through M4U are unavailable - that is a device-security feature
this port does not attempt, not a regression against what boots today.

**5.6 32-bit compat ioctls.** `MTK_M4U_COMPAT_ioctl` translated four commands
(`COMPAT_MTK_M4U_T_ALLOC_MVA/DEALLOC_MVA/CACHE_SYNC/DMA_OP`) by copying the compat struct into a
buffer from `compat_alloc_user_space()`. This 5.15 base has **no `fs/compat.c`** (not in the repo:
`git ls-files fs/ | grep compat` -> only `compat_binfmt_elf.c`), so neither that helper nor the
kernel's compat ioctl layer exists. The port therefore selects the vendor's own alternative - the
`#else` branch that defines `MTK_M4U_COMPAT_ioctl` as `NULL` - with the Kconfig condition extended to
`IS_ENABLED(CONFIG_COMPAT) && defined(M4U_HAVE_COMPAT_TRANSLATION)`. A 32-bit caller gets the VFS
default (`-ENOIOCTLCMD` -> `ENOTTY`) rather than a translation that cannot be built. Nothing in the
64-bit path changes; the four `compat_*` struct definitions stay in the file, inside the guard, so
re-enabling is a `-D` away once `fs/compat.c` is restored or the cases are rewritten onto
`m4u_ioctl()`'s own helpers.

## 6. Bindings, measured on the packaged DTB

`mediatek,m4u` is `m4u@10205000` with `cell-index = <0>`, `reg = <0x0 0x10205000 0x0 0x1000>`,
`interrupts = <0 0xae 8>`, `clocks = <&syscon_15020000 1>` (`"ISP_CLK_IMG_DIP"`). The driver binds it
through `iommu_of_ids` (`2.0/m4u.c:2339`: `mediatek,m4u`, `mediatek,iommu_v0`,
`mediatek,perisys_iommu`), `.name = "m4u"`, `subsys_initcall(MTK_M4U_Init)` ->
`platform_driver_register` -> `m4u_probe`, which turns `cell-index` into `pdev->id` (0 -> M4U0),
`of_iomap`s the register block and `irq_of_parse_and_map`s the fault IRQ, then runs
`m4u_domain_init()` + `m4u_hw_init()` (`request_irq()` at `m4u_hw.c:3000`).

Inside `m4u_reg_init()` the driver does its own DT lookups, and each was checked against the same
`.dtb` the image ships (`dtc -I dtb -O dts`, not the DTS source):

| string M4U looks up | DTB entries | note |
|---|--:|---|
| `mediatek,smi_common` (under `M4U_MMU_SLAVE_SWITCH`, defined for MT6768 at `m4u_priv.h:103`) | 1 | `smi_common@14002000` |
| `gM4U_SMILARB[]` = `mediatek,smi_larb0..4` (`m4u_platform.h:9`) | 1 each | the SMI driver's own match is the second entry of the same property, so `of_find_compatible_node()` resolves all five |
| `mediatek,pericfg` | 1 | used only under `#if (TOTAL_M4U_NUM > 1)`; MT6768 has `TOTAL_M4U_NUM 1`, so compiled out |

`bin/hwenable.py` on the built `.dtb` moved exactly one row this commit:

```
bound_by_5_15_driver   33 -> 34      enabled_in_this_build  24 -> 25
no_driver_in_5_15     316 -> 315     mediatek,m4u  NO_DRIVER -> ENABLED
                                      driver=drivers/misc/mediatek/m4u/2.0/m4u.c CONFIG_MTK_M4U=y
```

The DTB itself is untouched: `mt6768.dtb` is still `34a7e6b5...85a11cd`, 122,474 bytes, byte-identical
inside the packed `boot.img` (`out/boot.img.dump/dtb`). No `iommus`/`#dma-cells` conversion was done.
M4U does not consume the node's `clocks` cell (no `clk_get`/`clk_prepare_enable` anywhere in
`mt6768/m4u_hw.c`); `bin/clkaudit.py --require-fresh` re-run on build-36 is unchanged at 234 refs /
234 registered / 0 unresolved, with `m4u@10205000 -> CLK_IMG_DIP` still listed as registered, i.e.
the clock exists for whoever asks for it and M4U leaves it alone, exactly as stock does.

## 6.1 Boot-time behaviour, and why it is not a new risk

Probe runs from `subsys_initcall`, so it is on the boot path the moment the config is on, and two
things were checked rather than assumed:

- **The fault IRQ is not shared.** `m4u_hw_init()` does
  `request_irq(irq, MTK_M4U_isr, IRQF_TRIGGER_NONE, "m4u", NULL)` (`mt6768/m4u_hw.c:3000`) - no
  `IRQF_SHARED` - so a second claimant on the same line would make probe fail with -EBUSY. IRQ 174
  (`0xae`, level-high) appears on exactly one node of the shipped DTB, `m4u@10205000`
  (`grep -nE "interrupts = <0x00 0xae " mt6768.dts` -> 1 hit), so the line is M4U's alone.
- **What `m4u_hw_init()` programs.** `enable_4G()` for the DRAM-mode bit, the trace-protect buffer
  (`TF_PROTECT_BUFFER_SIZE` allocation, its PA with the bit32/bit33 above-4 GiB encoding), then
  `m4u_reg_init()` which writes the PGD base, the protect-range registers and the SMI common/larb
  bases it maps itself. It does not claim or enable media masters: a port only translates once a
  client calls `m4u_config_port()`, which is why the same code boots with `MTK_M4U=y` on the stock
  4.19 image and why nothing here can hang the display path that no one has opened.
The one deliberate difference from stock on that path is the SMI side: `smi_register()` (which sets
the `mm_first` mask) is not ported, and MT6768 reads that value only under `CONFIG_MACH_MT6765` or
`CONFIG_MACH_MT6761` - see `m4u-ion-audit.md`/KNOWN-ISSUES 10.4 - so the keep/unkeep calls in
`m4u_hw.c:1109-1124` behave identically here. No boot claim is made beyond that: the image is not
flashed, so this is a static reading of the path, not an observation of a running board.

## 7. Build, link, packaging

```
./run36.sh  ->  Image.gz-dtb modules
  compiler errors 0   make failures 0   undefined symbols 0
  objects 7372 -> 7377 (the five M4U units), .ko 840 (M4U is obj-y, as on stock)
  Image        26,966,024 -> 27,035,656   (+69,632 B)
  Image.gz     10,605,822 -> 10,648,429   (+42,607 B)
  Image.gz-dtb                  11,141,946
  vmlinux: m4u_alloc_mva, m4u_alloc_mva_sg, m4u_hw_init, m4u_reg_init, m4u_pgtable_init,
           m4u_debug_init, m4u_probe, MTK_M4U_Init  (all present; probe/init local `t`)
  M4U -> SMI: smi_bus_prepare_enable/smi_bus_disable_unprepare/mtk_smi_clk_enable/
              smi_get_dev_num/smi_mm_first_get resolve to drivers/memory/mtk-smi-mt6768.c
out/boot.img: 11,268,096 B, header v2, 2048 B pages, board/name RM6768, cmdline
              bootopt=64S3,32N2,64N2, pinned boot-id, partition 33,554,432 (33% used);
              extracted kernel == Image.gz-dtb (sha e14c0d4c...), extracted dtb == built .dtb.
```

`build.sh`'s one-off `scripts/extract-cert.c` openssl failure was avoided by invoking everything
through `./build.sh` (it passes the `tools/sslshim` flags); the earlier bare-`make` attempt in this
round died on that and is why the per-directory loop goes through the wrapper.

Maturity after this round: **source complete, build complete, flash/boot/function still no** - the
same gate as the SMI substrate, because nothing on the device opens M4U yet. What M4U unlocks is the
next client (display/video `ddp_m4u`), whose first requirement is a buffer source; that is where the
`ION_CMD_MULTIMEDIA` question resurfaces, and it is deliberately not answered here.
