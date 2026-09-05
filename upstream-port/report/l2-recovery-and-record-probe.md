# L2 after the recovery: gates re-run, and the record layer costed (measured 2026-09-05)

Two things happened in this round. The sandbox was reset again and the build environment was rebuilt
from the versioned recipe - which turned out to need three fixes, all now in the repo. Then the L2
gate was re-run in the reproduced tree and the next layer (the CMDQ *record* API, the one everything
else in dispsys waits on) was measured instead of guessed.

## 1. Recovery: what was missing and what was actually wrong

`/home/user/portwork/` was gone. Rebuilt with
`cp -a upstream-port/tools/portwork/. /home/user/portwork/ && cd /home/user/portwork && ./restore.sh`
(462 MB fetched: 368 MB build-tools, 94 MB gcc-9.3, shallow `gregkh/linux` @ `v5.15.220` = `0996e0926`).

Three defects surfaced, none of them in the kernel tree:

| # | symptom | cause | fix |
|---|---|---|---|
| 1 | `restore.sh` could not run at all | `tools/env.sh` was the one environment file that had never been versioned - it lived only in `portwork/`, so the reset removed it and the restore that is supposed to rebuild `portwork/` needed it | `env.sh` is now `upstream-port/tools/portwork/env.sh`, and `restore.sh` installs it from the repo if `cp -a` was skipped |
| 2 | `make defconfig` died in `scripts/basic/fixdep` with `as: unrecognized option '--64'` | the newly written `env.sh` put the SDK's `aarch64-buildroot-linux-gnu/bin` on `PATH`; that dir holds the **AArch64** `as`, `ld`, `ar`, `nm` under **unprefixed** names, so it shadowed the host binutils used for host tools | that dir is off `PATH` now, with the failure recorded in the file. The kernel reaches binutils as `${CROSS_COMPILE}ld` etc., all of which resolve through `tools/gcc/bin`. Gates that read aarch64 objects must call `${CROSS_COMPILE}nm` explicitly - `/usr/bin/nm` here is x86-only |
| 3 | `make defconfig` then died in `scripts/kconfig/parser.tab.h` | the build-tools `bison` is a relocated Bazel build: its `pkgdatadir` is baked as `/nonexistent/common/bison` (its `m4sugar` data files therefore unresolvable) and its m4 path is baked as `/usr/bin/m4`, which this image does not have. `BISON_PKDATADIR` is ignored and there is no `--datadir` option. Compounding it, the old `restore.sh` copied `$src/common` where `$src` is `linux-x86/` - bison's data is at the **tarball root** (`common/bison`), so the copy silently did nothing | `restore.sh` now copies `common/` from the tarball root, links `/nonexistent -> $ROOT/tools/build-tools` (needs write permission on `/`; `sudo -n` works here, so it is best-effort with a printed fallback), exports `M4=$ROOT/tools/build-tools/bin/m4` from `env.sh`, and **proves bison end to end** before `make` ever runs, because inside a build this failure is only `Error 1` on a `.h` file |

## 2. Gates re-run after recovery, in the reproduced tree

    gate                                     result
    git am 0001-0084 onto 0996e0926          rc=0, 85 commits, dirty=0,
                                             tree 3fa1c650082e917773ac00d2190befb35d575572  (== recorded)
    git am 0001-0083 (fresh worktree)        rc=0, tree 1bbd779ea9182f344c9e231621bca0ae8b715dae (== recorded)
    make ARCH=arm64 defconfig                rc=0
    configs/apply.sh                         all 15 recorded symbols present, .config sha256 758ae54339bf
    make prepare                             rc=0; scripts/dtc/dtc, kconfig/conf, modpost built
    slice build (-k, obj dir cleared first)  rc=0, 0 error: lines
    objects                                  14/14 present and non-empty
    ${CROSS_COMPILE}nm, link-visible defs    248 symbols, 0 defined twice
    ${CROSS_COMPILE}nm -u                    220 distinct unresolved names (see 4)

Object sizes in this tree vs the ones recorded for `amgate84`:

    ddp_dump.o 465,024 B here / 465,032 B recorded      ddp_color_format.o 68,976 / 68,984
    ddp_mutex.o 111,112 / 111,120                       ddp_manager.o 200,144 / 200,152

Every one differs by 0-8 bytes, and the difference is the `__FILE__` string: the recorded numbers came
from `/home/user/portwork/amgate84/...`, these from `/home/user/portwork/series/...`. **The invariant is
the object set and its non-emptiness, not the byte counts**; quoting sizes from a different checkout path
will always differ a little. `l2-slice-gate.sh` therefore derives the object list from the Makefile in
the tree it builds, which is also how the 13-vs-14 error was prevented from recurring.

## 3. The new gate script

`upstream-port/tools/portwork/l2-slice-gate.sh` (+ `upstream-port/bin/undeps.py`) is now the record of
this gate: tree identity, clean rebuild, per-object existence/size derived from `obj-y` in the tree,
duplicate link-visible definitions, and the unresolved-external classification. Run it as

    TREE=/home/user/portwork/series ./l2-slice-gate.sh --expect-tree 3fa1c650...

## 4. Unresolved externals, classified rather than feared

`nm -u` over a tree with 82 of ~7,400 objects is meaningless unless the names are attributed. Of the 220:

| class | count | meaning |
|---|---|---|
| satisfied | 66 | another object built in this tree defines it |
| core (vmlinux) | 64 | declared in a mainline header (`snprintf`, `vunmap`, `kmalloc_caches`, ...). Provider is the rest of the kernel; **not a blocker** |
| provider landed, not built here | 3 | `disp_helper_get_option/_stage/_init` - `video/mt6768/videox/disp_helper.c` is IN the tree but no `obj-y` line builds it. Real wiring gap, one line, independent of every open question |
| PROVIDER NOT LANDED | 70 | grouped by the vendor file that defines them, this *is* the dependency map: `ddp_path.c` 12, `ddp_dsi.c` 6, `primary_display.c` 6, `ddp_rdma_ex.c` 6, `ddp_mmp.c` 5, `ddp_ovl.c` 5, `cmdq_record.c` **4**, `ddp_disp_bdg.c` 3, `disp_lowpower.c` 3, then 2s and 1s |
| unattributed | 17 | data symbols, not functions: `ddp_driver_*` (the per-module `struct ddp_hal_driver` objects in the not-yet-landed layer files), `g_mobilelog`, `module_list_scenario`, plus core items (`__stack_chk_fail`, `arm64_use_ng_mappings`) |

The `cmdqRecWrite` / `cmdqBackup{Allocate,Read,Write}Slot` quartet is the 4 attributed to
`cmdq_record.c`, and it is the only CMDQ entry point the landed 14 objects still miss.

## 5. The record layer, measured (this was the round's real objective)

Method: a fresh worktree at the published 0084 tree, `l2slice.py --srcdir cmdq/v3 --objs cmdq_record.c`,
so the compiler - not a grep - decides what is missing. The probe needed `l2slice.py` fixes first: its
build goal was hardcoded to `dispsys/` (it had been silently "building" the wrong directory and calling
the absence of `cmdq_record.o` a Makefile bug), and a kbuild-level failure is not a compile failure -
a directory is only built when an already-descended `Makefile` names it
(`drivers/misc/Makefile: obj-y += mediatek/video/`, then
`video/Makefile: obj-$(CONFIG_MTK_DISP_M4U) += mt6768/dispsys/ mt6768/videox/`). Any record-layer slice
must add the same kind of line for `cmdq/`; without it a build "succeeds" having compiled nothing.

What the probe found:

* **Include closure: 2 extra headers, nothing else.** `cmdq_virtual.h`, `cmdq_sec.h`. The 7 v3 headers
  carried by 0084 already cover the rest, including the `struct timeval` -> `timespec64` adaptation.
* **`cmdq_record.c` is self-contained: 4,141 lines, 0 references to any global defined in another v3
  `.c`, and every function it calls is defined in the same file** - except the client API and
  `cmdq_mmp_get_event()` (config-gated `CONFIG_MMPROFILE`, off). The rest of the v3 engine
  (26,437 lines in 15 files: `cmdq_driver.c`, `cmdq_device.c`, `cmdq_helper_ext.c`, `cmdq_sec*.c`,
  `cmdq_test.c`, `cmdq_mdp_common.c`, `cmdq_virtual.c`, `mt6768/cmdq_mdp.c`) is **not** pulled by the
  record layer. "Do not carry the whole vendor v3 engine unless a live display callsite proves it
  required" is now measurable, and the measurement says the engine is not required here.
* **Compile result: 159 error lines, all at one boundary - `struct cmdq_pkt`.** The record file keeps
  its own cursor over the packet buffer and so touches the packet internals directly:
  `cmd_buf_size` 36x (mainline has it), `buf_size` 1x (has it), and then
  `avail_buf_size` 8x, `buf` 5x, `priority` 4x, `dev` 2x, `loop` 2x, `user_data` 1x - **6 members and
  22 references that mainline 5.15's 7-member `struct cmdq_pkt` does not have**. Same story in the
  shared headers: `include/linux/mailbox/mtk-cmdq-mailbox.h` is 279 lines in the vendor tree vs 93
  here, `include/linux/soc/mediatek/mtk-cmdq.h` 434 vs 298, and `enum cmdq_code` has 22 vendor values
  vs 10 here - the 13 missing ones being `READ`, `WRITE_S_W_MASK`, `WRITE_FROM_REG`, `WRITE_FROM_MEM`,
  `MOVE`, `RAW`, `SET_TOKEN`, `CLEAR_TOKEN`, `WAIT_NO_CLEAR`, `JUMP_C_ABSOLUTE`, `JUMP_C_RELATIVE`,
  `PREFETCH_ENABLE`, `PREFETCH_DISABLE` (plus `SLEEP`/`LOGIC_*`/`COND_*` on the definition side).
* **Demand across the whole display chain, not just this slice: 31 distinct entry points, 453
  callsites, 12 files** (`cmdqRecReset` 67, `cmdqRecCreate` 55, `cmdqRecDestroy` 47, `cmdqRecWait` 33,
  `cmdqRecClearEventToken` 32, `cmdqBackupReadSlot` 31, ... down to 1). Guard-resolved census: the
  secure-path entry points (`cmdqRecWriteSecure` 6, `cmdqRecSecureEnableDAPC` 2) and the loop/count ones
  are **live, unguarded** on this board - they cannot be compiled out, so the record surface is the
  whole 31, not a subset.
* `cmdqRecCreate()` is a one-line wrapper over `cmdq_task_create()`, which is *inside* `cmdq_record.c`,
  and that function obtains its packet via `cmdq_pkt_create(...)` - i.e. the submission path bottoms
  out in mainline's client API, which is where 0082/0083 fixed the boundary.

## 6. Consequences, and what is NOT concluded

* The display core remains **compile-verified, not linkable**, and nothing here changes that. No
  `vmlinux`, no `Image`, no device behaviour is claimed, and the pre-0084 full-image gates
  (build-37: `Image` 27,035,656 B, `Image.gz-dtb` 11,141,441 B, `mt6768.dtb` 122,474 B, `boot.img`
  11,268,096 B) have **not** been re-run since 0082/0083/0084 landed - the full-image state after 0084
  is UNKNOWN in this sandbox.
* The next layer is sized by these numbers, but its *shape* is not a dependency-order detail: adding 6
  members to mainline's `struct cmdq_pkt` and 13 opcodes to `enum cmdq_code` means growing the shared
  CMDQ ABI that 0082 was created to protect, and mainline's mailbox driver (`mtk-cmdq-mailbox.c`)
  allocates and owns that packet buffer today. That is an architectural and hardware-risk decision -
  wrong GCE instruction encoding is a panel that stays black or a display that corrupts at vblank - so
  it is put to the human rather than resolved by preference. The options and their measured costs are
  in `report/l2-record-layer-options.md`; decision 139.
* A `disp_helper.o` wiring line is owed either way, and is deliberately *not* bundled into this
  measurement round: one change per verified slice.
