# The first display/video client on the M4U path

Status of this round: the display-side M4U client glue is **traced, ported, built,
linked and host-executed**. Nothing here is flashed or run on the phone.

| level | state | evidence |
|---|---|---|
| source ported | yes | 12 files, 1,110 lines (10 new, 2 wiring edits) - `drivers/misc/mediatek/video/**` |
| builds and links | yes | build-37: 0 errors, 0 warnings, 0 undefined references, objects 7377 -> 7379 |
| DT binding verified | yes (negative result) | no new binding by design; `mediatek,dispsys` / `mediatek,mtkfb` stay `NO_DRIVER`, `mediatek,m4u` stays `ENABLED` |
| runtime validated | host only | `upstream-port/tests/` runs the ported client: 43 checks, 0 failures; client-facing M4U ABI byte-identical to the 4.19 vendor headers |
| flash-ready | no | unchanged from before: no verified boot.img layout / AVB / board-id source |
| boot-tested | no | no board. Emulation unavailable: `qemu-system-aarch64` is not installable in this sandbox (apt has no package source) |
| function-tested | no | no panel is driven; nothing calls the client yet |

## 1. What the display tree actually is, measured before porting

`drivers/misc/mediatek/video` in the 4.19 reference tree, C sources only:

| directory | lines | role |
|---|---|---|
| `mt6768/dispsys/` | 34,419 | the MT6768 display core (DDP): ddp_dsi 8,377 / ddp_disp_bdg 5,263 / ddp_ovl 2,823 / ddp_manager 2,170 / ddp_drv 705 / **ddp_m4u 400** |
| `mt6768/videox/` | 36,982 | legacy fb path: primary_display 10,857 / mtkfb 3,134 / disp_lcm 2,143 / disp_helper 453 |
| `common/*/` | 10,328 | shared IP blocks (IPv1, aal30, color20, corr10, rdma20, wdma20, pwm10, layering_rule_base) |
| `common/mtkfb_dummy.c` | 815 | dummy fbdev |
| `mtdummy/mtkfb.c` | 550 | second dummy fbdev |
| whole `video/` tree, all chips | 647,104 | |

Which of it stock even compiles (`arch/arm64/configs/even_defconfig`: `CONFIG_MTK_FB=y`,
`CONFIG_MTK_LCM=y`):

* `video/Makefile:32` `ifneq ($(CONFIG_MTK_LCM), y) obj-y += mtdummy/` -> **`mtdummy/` excluded**.
* `common/Makefile:103` `ifneq ($(CONFIG_MTK_FB), y) obj-y += mtkfb_dummy.o` -> **`mtkfb_dummy.o` excluded**
  (`mt6768/videox/Makefile` carries the matching comment `# ... already in video/common/`).
* `mt6768/Makefile` builds `dispsys/` **and** `videox/` under `CONFIG_MTK_FB=y`.
* `CONFIG_MTK_VIDEOX` is **vestigial in this BSP**: it appears only in `video/Kconfig` and in
  zero Makefiles, so it gates nothing. (An earlier reading in this project assumed it disabled
  `videox/`; the Makefiles say otherwise, and that assumption would have mis-scoped this port.)

So the boot-visible display path on this product is roughly **81.7k lines** - far beyond one
client, which is why the chain was traced first instead of transplanted.

## 2. The traced allocation -> SMI -> M4U chain

The first *boot-visible* chain that reaches `m4u_alloc_mva` is not the panel path, it is the
LK-logo handover:

```
LK reserves the logo FB
  -> videox/mtkfb.c:2648   disp_hal_allocate_framebuffer(fb_base, fb_base+vramsize-1, &va, &mva)
       [video/mt6768/dispsys/ddp_m4u.c:338]
       ioremap_wc(pa_start, len)                     <- kernel VA for the same pages
       sg_alloc_table(sgt, 1, GFP_KERNEL)            <- ONE entry, no ION, no dma-buf heap
       sg_dma_address(sgt->sgl)   = pa_start
       sg_dma_len(sgt->sgl)       = pa_end-pa_start+1
       m4u_create_client()                            <- drivers/misc/mediatek/m4u/2.0/m4u.c
       m4u_alloc_mva(client, DISP_M4U_PORT_DISP_OVL0, 0, sgt, size,
                    M4U_PROT_READ|M4U_PROT_WRITE, 0 /*flags*/, (unsigned int *)&mva)
         -> m4u.c: m4u_alloc_buf_info, m4u_do_mva_alloc, m4u_map_sgtable(
              m4u_get_domain_by_port(port), ...)      <- MVA interval + page tables
         -> m4u_hw.c (mt6768): programs the port's larb through drivers/memory/mtk-smi
  -> videox/primary_display.c:4113 config_display_m4u_port()      [ddp_m4u.c:99]
       m4u_config_port({ePortID, Virtuality=1, Security=0, Distance=1, Direction=0})
       for OVL0, OVL0_2L, RDMA0, WDMA0
  -> dispsys/ddp_drv.c:557 disp_m4u_init()                         [ddp_m4u.c:71]
       m4u_register_fault_callback(port, disp_m4u_callback, 0) x4
  -> dispsys/ddp_drv.c:593 disp_helper_option_init()               [videox/disp_helper.c:338]
       disp_helper_set_option(DISP_OPT_USE_M4U, 1)   <- after this, the M4U branches are live
```

Two findings from the trace that changed the port:

1. **`disp_m4u_init()` runs *before* the option that enables M4U.** Stock calls it at
   `ddp_drv.c:557` and `disp_helper_option_init()` at `ddp_drv.c:593`, while the table default
   is `{DISP_OPT_USE_M4U, 0, ...}` (`disp_helper.c:71`, commented "must enable"). So on MT6768
   the *else* branch of `disp_m4u_init()` is live code at dispsys probe: it clears `MMU_EN` in
   `SMI_LARB0` `CON0..CON3`. That is a dispsys/SMI ownership question, not a client question,
   and it is flagged for whoever ports the core (see the Port comment in the file).
2. **The dummy fbdev never touches M4U.** `common/mtkfb_dummy.c` calls
   `disp_hal_allocate_framebuffer()` only in its `#else` (non-`CONFIG_OF`) branch; with `CONFIG_OF`
   it uses its own local `mtkfb_allocate_framebuffer()`, which just sets `*mva = pa_start`.
   Neither dummy is even built in stock (section 1), and the `atag,videolfb-*` properties the
   vendor reads are absent from the packaged `mt6768.dtb` (0 matches), so the logo handover
   depends on whatever LK injects at boot - one more reason no boot claim is made here.

## 3. ION: traced, and not required

`ddp_m4u.c` contains 41 `ion_` references, all inside the seven `disp_ion_*()` wrappers, and
every body is guarded by the vendor's own `#if defined(MTK_FB_ION_SUPPORT)`. That macro is not a
Kconfig symbol: it appears in no `Kconfig` and no `Makefile` in the tree (it comes from the
Android userspace build), so in a kernel-only build those bodies were already compiled out.

Consequently **no ION and no dma-buf heaps were added**. The wrappers were deleted together with
the ION types their prototypes need (`struct ion_client`, `struct ion_handle`,
`enum ION_CACHE_SYNC_TYPE` from `mtk_ion.h`/`ion_drv.h`/`ion_priv.h`, which v5.15 does not
carry). `report/m4u-ion-audit.md` section 8 remains the record of what that ABI provides and why
a client on this tree books mappings through `m4u_alloc_mva()` directly - which is exactly what
the traced chain does.

## 4. What was ported, and every edit

New in the 5.15 tree (1,110 lines total, 2 objects built):

| file | lines | origin |
|---|---|---|
| `video/Kconfig` | 29 | new: `MTK_DISP_M4U` (depends on `MTK_M4U`, default y) |
| `video/Makefile` | 4 | new: `obj-$(CONFIG_MTK_DISP_M4U) += mt6768/dispsys/ mt6768/videox/` |
| `video/mt6768/dispsys/Makefile` | 18 | new: `obj-y += ddp_m4u.o` + trimmed include list |
| `video/mt6768/videox/Makefile` | 9 | new: `obj-y += disp_helper.o` |
| `video/mt6768/dispsys/ddp_m4u.c` | 249 | vendor 401 lines, trimmed |
| `video/mt6768/dispsys/ddp_m4u.h` | 66 | vendor 72 lines, trimmed |
| `video/mt6768/dispsys/ddp_log.h` | 51 | **new port-local log layer** |
| `video/mt6768/dispsys/ddp_hal.h` | 140 | vendor verbatim (`enum DISP_MODULE_ENUM`) |
| `video/mt6768/videox/disp_helper.c` | 452 | vendor 453 lines, trimmed |
| `video/mt6768/videox/disp_helper.h` | 98 | vendor verbatim |
| `drivers/misc/Kconfig`, `drivers/misc/Makefile` | +2 | wire the new directory, same style as `m4u/` |

Edits to vendored files, with what each predicted and what actually happened:

| # | edit | why | build result |
|---|---|---|---|
| 1 | drop `ion_priv.h`, `mtk_ion.h`, `ion_drv.h` includes; delete the seven `disp_ion_*()` wrappers + prototypes (158 lines) | ION headers do not exist on v5.15; bodies were already compiled out by `MTK_FB_ION_SUPPORT` | predicted: clean. actual: `ddp_m4u.o` compiled with 0 warnings on the first try |
| 2 | replace the `DISP_REG_SET_FIELD(... MMU_EN ...)` fallback with a `pr_warn` | `ddp_reg.h` drags `display_recorder.h`, `cmdq_record.h`, `cmdq_core.h` + 8 `ddp_reg_*.h`; the LARB registers belong to `drivers/memory/mtk-smi` on this tree | predicted: one fewer dependency. actual: no `cmdq` include needed at all |
| 3 | `ddp_get_module_name(module)` -> print the enum value | name table lives in `ddp_info.c` (612 lines) whose `ddp_modules[]` needs the dispsys register-info table | predicted: log-text-only change. actual: as predicted |
| 4 | `disp_m4u_callback()`: drop `ddp_dump_analysis()`/`ddp_dump_reg()` | `ddp_dump.c` is 1,643 lines of register reads through the unported layer | predicted: callback keeps logging, loses register dump. actual: as predicted, documented in file |
| 5 | new port-local `ddp_log.h` | vendor `ddp_log.h` *and* `disp_drv_log.h` route every message through `dprec_logger_pr()` (`display_recorder.c`, 1,657 lines) and `ddp_debug.c` (964) | semantic difference: these messages reach the kernel log only, `/dev/pmsg/dprec` mirror unavailable; `DDPMSG` is unconditional `pr_info` instead of gated on `g_mobilelog` |
| 6 | `disp_helper.c`: remove `primary_display.h`, `mtk_boot.h`, `mt-plat/mtk_chip.h`, `disp_drv_platform.h` includes | they supply only the videox/DynFPS/boot-state couplings; keeping them would pull the legacy fb headers | predicted: 4 includes drop cleanly. actual: as predicted |
| 7 | `disp_helper_set_option()`: remove the `DISP_OPT_FPS_CALC_WND` -> `primary_fps_ctx_set_wnd_sz()` hook | defined in `primary_display.c` (10,857 lines), not ported | predicted: option becomes a pure table entry. actual: as predicted (the `-Wunused-variable` that would have followed was avoided by dropping `int ret` with it) |
| 8 | `disp_helper_get_option()`: `#ifdef CONFIG_MTK_FB` around the `FAKE_LCM_WIDTH/HEIGHT` cases | they call `primary_display_get_virtual_width()`/`DISP_GetScreenWidth()` (first link-blocking error found: `-Werror=implicit-function-declaration`, 4 errors) | predicted: falls back to the table (0 = no fake LCM). actual: as predicted; guarded by the symbol that gates videox, so a future full port keeps stock behaviour |

Nothing else was needed: the client resolves against the already-ported `m4u/2.0`, `m4u/mt6768`
and mmp/sync_write headers, and `<soc/mediatek/smi.h>` is not needed at all (that include is
inside the `CONFIG_MTK_IOMMU_V2` branch, which stock does not enable).

## 5. Build, link and binding verification (build-37)

```
compiler_errors=0   make_failures=0   undefined=0   warnings=0
objects=7379 (build-36: 7377, +2 = exactly the two new objects)
modules_ko=840 (unchanged - both files are obj-y built-ins)
Image        27,035,656 B   (identical to build-36; the +6 KB of client text is absorbed by
                             section padding - and the config self-check plus the identical
                             driver tables below show no driver was lost or gained)
Image.gz     10,647,924 B   Image.gz-dtb 11,141,441 B (appended payload 493,517 B, same 6-blob
                             layout as build-36: mt6768.dtb + 5 .dtbo, first FDT at 10,647,924)
mt6768.dtb   122,474 B  sha256 34a7e6b5...a11cd   UNCHANGED (no DT edit in this round)
dtbo.img     371,235 B  sha256 38fe681f...        UNCHANGED (byte-identical rebuild)
boot.img     11,268,096 B  sha256 e4789535...      kernel section 11,141,441 B, dtb 122,474 B
```

Symbols in `System.map` (all present, and the client's undefined M4U references resolve into the
ported driver, not into stubs):

```
T disp_m4u_init  T disp_m4u_callback  T config_display_m4u_port  T disp_mva_map_kernel
T disp_mva_unmap_kernel  T disp_allocate_mva  T disp_hal_allocate_framebuffer
T module_to_m4u_port  T module_to_m4u_larb  T m4u_port_to_module
T disp_helper_get_option  T disp_helper_option_init
   -> m4u_alloc_mva / m4u_create_client / m4u_mva_map_kernel  in m4u/2.0/m4u.o
   -> m4u_config_port / m4u_register_fault_callback           in m4u/mt6768/m4u_hw.o
```

DT binding, `hwenable.py` (run against the tree, not against `--compat-index`): bound 34,
enabled 25, enableable 5, driverless 315 - **identical to build-36, changed rows: none**. The
expected result for this round is a *negative* one: the ported unit is the client side of the
driver interface and has no `of_device_id` table of its own, so it must not steal a node;
`mediatek,dispsys` and `mediatek,mtkfb` remain `NO_DRIVER` until the dispsys core lands, and
`mediatek,m4u` remains `ENABLED` via `drivers/misc/mediatek/m4u/2.0/m4u.c`.
`clkaudit.py` unchanged: 234 refs / 234 registered / 0 unresolved.

## 6. Runtime-oriented validation: executing the client on the host

There is no board and no QEMU in this sandbox, so the client's control flow is executed for real
on the host instead: `upstream-port/tests/run-disp-m4u-host-test.sh` compiles **the same
`ddp_m4u.c` and `disp_helper.c` that are in the tree** with `CONFIG_MTK_M4U=1` and
`MTK_FB_ION_SUPPORT` undefined (the stock kernel configuration) against the **real** ported M4U
headers, and drives them with a recording M4U stub:

```
$ upstream-port/tests/run-disp-m4u-host-test.sh /home/user/portwork/build /home/user/Zenium_Kernel out.json
=== summary: 43 checks, 0 failed ===
VERDICT PASS
RESULT abi_identical=pass
```

What the run establishes (`report/display-m4u-client.json` holds every line):

* `disp_helper_get_option(DISP_OPT_USE_M4U)` is **0** before `disp_helper_option_init()` and **1**
  after - the exact sequencing behaviour the trace predicted, i.e. `disp_m4u_init()` at
  `ddp_drv.c:557` really does see the "M4U off" state on stock MT6768.
* The port table maps OVL0/OVL0_2L/RDMA0/WDMA0 to `M4U_PORT_*` = 0/1/2/3 (driver values), all four
  on larb 0, and `M4U_PORT_NR == M4U_PORT_UNKNOWN`, so `disp_allocate_mva()`'s
  `port == M4U_PORT_NR` guard is a genuine "unknown module" rejection (returns 1) - it does not
  reach the driver, verified: 2 allocs recorded, not 3.
* `disp_m4u_init()` registers **4** fault callbacks, one per port, each pointing at
  `disp_m4u_callback`; invoking the RDMA0 one resolves the module back through the table and
  returns 0, and calling it with `M4U_PORT_UNKNOWN` is safe.
* `config_display_m4u_port()` issues **4** `m4u_config_port()` calls with
  `Virtuality=1, Security=0, Distance=1, Direction=0` and the table's port order.
* A latent vendor detail, observed rather than assumed: `struct m4u_port_config_struct.domain`
  comes back as the `0xa5a5a5a5` stack poison, i.e. **the client never initialises it**. It is
  harmless on MT6768 because M4U v2.0 has a single domain and `m4u.c:806/995` derive the domain
  from the port (`m4u_get_domain_by_port()`); recorded here so a multi-domain port does not
  inherit it silently.
* The FB handover passes to the driver: `size == pa_end-pa_start+1`, one sg entry with
  `dma_address == pa_start` and `length == size`, `prot == M4U_PROT_READ|M4U_PROT_WRITE`,
  `flags == 0`, `va == 0`, and `ioremap_wc(pa_start, size)` for the kernel VA.
* The client *pre-sets* `*mva = pa_start & 0xffffffff`, but because `flags == 0` the driver does
  not honour it (`m4u.c`: fixed MVA requires `M4U_FLAGS_FIX_MVA`); the returned MVA is what the
  caller must program. The test asserts the returned value, not the pre-set one - the difference
  matters for any future code that assumes MVA == PA for the logo.
* `m4u_mva_map_kernel()` receives `(mva, size, &map_va, &map_size)`, and
  `disp_mva_unmap_kernel()` calls `vunmap()` on `map_va & ~PAGE_MASK`.
* Failure path: with `sg_alloc_table()` forced to fail, `disp_hal_allocate_framebuffer()` returns
  `-ENOMEM` and **no** M4U call is made.
* ABI probe: the same probe compiled against the ported 5.15 headers and the 4.19 vendor headers
  is **identical** - `M4U_PORT_NR=61`, display port IDs 0/1/2/3,
  `sizeof(struct m4u_port_config_struct)=24`, `Virtuality@4 domain@12 Distance@16 Direction@20`,
  `M4U_PROT_READ=1 WRITE=2`, `M4U_FLAGS_FIX_MVA=2 SG_READY=16`.

Boundary of this evidence, stated plainly: the M4U side of the harness is a recorder. It proves
what the *client* does and that both sides agree on the ABI; it proves nothing about MMIO writes,
translation correctness, SMI/LARB state, IRQ 174 behaviour or boot. Those need the board.

## 7. What still stands between this and a working display

* `ddp_m4u.c` has no caller in this tree. Wiring `disp_m4u_init()` +
  `config_display_m4u_port()` into a probe of the existing `mediatek,dispsys` node was
  deliberately not done: with USE_M4U=1 those calls switch the four display ports to virtual
  addressing while LK keeps scanning out the logo, and doing that without the register-layer
  owner (the dispsys core) is how you black a panel. A board-side test should be a
  `CONFIG`-gated, opt-in boot test over a plain `dma_alloc_coherent()` buffer, not a partial
  probe.
* The remaining closure, measured: dispsys core 34,419 lines (of which `ddp_dsi` 8,377 and
  `ddp_disp_bdg` 5,263), videox 36,982, shared IP 10,328, plus LCM drivers, cmdq v3,
  `display_recorder`, `ddp_debug`/`ddp_mmp` (mmprofile), and the `CONFIG_FPGA_EARLY_PORTING` /
  GED / dramc include coupling the vendor Makefiles assume.
* Buffer allocation for real clients: this tree offers `m4u_alloc_mva()` with a caller-supplied
  `sg_table` (`M4U_FLAGS_SG_READY`) - no ION, no heaps. A client that insists on
  `ION_CMD_MULTIMEDIA`/`ion_mm_data` needs that ABI ported first, and that decision is the user's,
  not something to smuggle in as a dependency.

## 8. How the config regression in this round was caught

The first build-37 attempt was 20,480 bytes *smaller* than build-36 while adding code, and
`Image.gz-dtb` came out as a byte-for-byte copy of `Image.gz`. Cause: re-running
`./build.sh configure` regenerates `.config` from arm64 `defconfig`, which silently dropped
`MACH_MT6768` (and with it `PINCTRL_MT6768`/`MTK_DEVAPC`), `COMMON_CLK_MT6768`,
`MEDIATEK_MT6577_AUXADC`, `MT635X_AUXADC`, `RTC_DRV_MT6397`, and both
`BUILD_ARM64_APPENDED_DTB_IMAGE`/`*_NAMES` symbols. The two size symptoms were the only output
evidence; `hwenable.py` then named the eight regressed rows exactly, and the previous
report's `kconfig` column gave the symbols to restore. Both are now codified:
`portwork/configs/apply.sh` sets the recipe and self-checks it, and the rejected attempt is kept
as `logs/build-37a-rejected.log` / `logs/run37a-rejected.out`. After restoration:
`Image` size back to build-36's value, `enabled_in_this_build` 17 -> 25, changed rows none.

Related precision fix: `artifacts.json` recorded the mkbootimg round-trip as differing in 21
header bytes because "unpack records neither name nor board". Re-measured with the same geometry
flags passed to `verify`, the re-pack is now **byte-identical including the header page** - the
earlier difference was the missing `--name/--board` on the *verify* invocation, not a property of
the image. Corrected in `report/artifacts.json`.
