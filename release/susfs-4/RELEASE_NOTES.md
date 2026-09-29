# Zenium Kernel RUI4 V1.6 — susfs-4 (+ NoMount v2.0.0)

This is the same kernel as `susfs-4`, with **NoMount v2.0.0**
([maxsteeel/nomount](https://github.com/maxsteeel/nomount)) integrated on top of
SUSFS v2.3.0 + ReSukiSU. Nothing in SUSFS, ReSukiSU or any vendor/Oplus code
was modified to add it — NoMount is fully self-contained in `fs/nomount/`.

| Component | Version | Mechanism |
|---|---|---|
| KernelSU / ReSukiSU | **35154** (`v4.2.0-rc2-6ec8d9a8@ReSukiSU`) | submodule `6ec8d9a8a8be30878c388504cacf8ae7849c757b`, 4454 commits |
| SUSFS | **v2.3.0** (NON-GKI) | inline hooks in `fs/*`, `mm/*`, `security/*`, `drivers/input/input.c`, `kernel/*` |
| NoMount | **v2.0.0** (`NOMOUNT_VERSION "20"`, upstream `6b1be18`) | VFS `i_op`/`d_op`/`s_op` hijacking, entirely inside `fs/nomount/` |

If you flashed the earlier `susfs-4` zip (`…-susfs-4.zip`, 20,618,357 B) and your
ReSukiSU manager complained, that bug is fixed here too — the manager-rejection
cause (`KSU_VERSION 30701` from a shallow submodule clone) is explained at the
bottom of this file and is gone in every build produced by
`scripts/build_susfs.sh` since `susfs-4`.

---

## 1. What NoMount is and why it does not disturb SUSFS

NoMount is a path-redirection and virtual-file-injection subsystem. It works
**without mounting anything** and **without KernelSU support**: it registers a
kernel `key_type` called `nomount`, and the userspace `nm` CLI hands it a
payload pointer through `add_key()`. On a rule it takes over the `inode_operations`,
`dentry_operations` and `super_operations` of the targeted inode so that
`openat()`/`stat()`/`readdir()` on that path transparently serve redirected or
injected content.

There is **no code overlap** with SUSFS or ReSukiSU:

* NoMount lives entirely in `fs/nomount/{Kconfig,Makefile,nomount.c,nomount.h}`.
  No existing file in the tree was modified to add it — only three new lines
  (`fs/Kconfig`, `fs/Makefile`, `arch/arm64/configs/even_defconfig`).
* `grep -rin nomount KernelSU/` returns **zero hits**: ReSukiSU/ReSukiSU has no
  NoMount code, no NoMount hooks and no NoMount config.
* NoMount's only kernel entry point is `fs_initcall(nomount_init)`, which just
  registers the key type. It does nothing at all until userspace adds a rule.
* SUSFS patches 25 existing files; NoMount patches none of them. The two
  mechanisms touch disjoint code.
* Symbols are disjoint: NoMount uses only `nomount_*` / `nm_*`, SUSFS only
  `susfs_*`, ReSukiSU only `ksu_*`. The link reports no duplicate definitions.

The combination is proven prior art — the branch
[`1.5.2_sus_Nomount-v2.0.0`](https://github.com/Rocker14427c/Zenium_Kernel/tree/1.5.2_sus_Nomount-v2.0.0)
ships susfs v2.2.0 + ReSukiSU v35040 + NoMount v2.0.0 together. This build moves
to the **current upstream NoMount revision** (`6b1be18`) rather than that
branch's older one.

---

## 2. Integration points (only these three lines)

| File | Line | Change |
|---|---|---|
| `fs/Kconfig` | 331 | `source "fs/nomount/Kconfig"` — inserted immediately before the last `endmenu` |
| `fs/Makefile` | 19 | `obj-$(CONFIG_NOMOUNT) += nomount/` — directly under the existing `obj-$(CONFIG_KSU_SUSFS) += susfs.o` (line 18) |
| `arch/arm64/configs/even_defconfig` | 5113–5114 | comment + `CONFIG_NOMOUNT=y` |

The four `fs/nomount/*` files are **byte-identical** to upstream
`maxsteeel/nomount@6b1be18`:

| File | Size | MD5 |
|---|---:|---|
| `fs/nomount/Kconfig` | 234 B | `e949ee4cc82260a9f042c8e3f35355b5` |
| `fs/nomount/Makefile` | 117 B | `30fa955d481445c4804b7974d45034e2` |
| `fs/nomount/nomount.c` | 62,149 B | `aae755a4f44464519b72d9d43916453b` |
| `fs/nomount/nomount.h` | 11,840 B | `8fb4ee12b139d3645a1412498f946c1a` |

### 4.19 compatibility pre-flight

Every `LINUX_VERSION_CODE` guard in `nomount.c` was checked against this tree
before building. For 4.19 all of them resolve to the *older* arm:

| Guard | Arm taken on 4.19 | Verified in this tree |
|---|---|---|
| `< 5.12` | no `mnt_idmap` in `i_op` | 4.19 `inode_operations` has no `mnt_idmap` |
| `< 6.6` | uses `iterate` | `include/linux/fs.h:1813` has **both** `iterate` and `iterate_shared` |
| `< 6.16` | no `mmap_prepare` | 4.19 `vm_operations_struct` has no `mmap_prepare` |
| `< 6.14` | old `d_revalidate` signature | `include/linux/dcache.h:135` `d_revalidate(dentry, flags)` |
| `< 5.0` | no `MODULE_IMPORT_NS` | not present in 4.19; the code does not reference it |
| `< 4.11` | old path-based `getattr` | **matches** — `include/linux/fs.h:1873` `getattr(const struct path *, struct kstat *, u32, unsigned int)` |
| `< 4.19` (`DCACHE_DONTCACHE`) | guarded away | NoMount itself `#ifdef`s the `DCACHE_DONTCACHE` path |

`register_key_type()` and the `key_preparsed_payload` interface exist in 4.19
(`security/keys/`), and `nomount_key_preparse()`'s `capable(CAP_SYS_ADMIN)` check
works unchanged.

---

## 3. Build

`bash scripts/build_susfs.sh` → **exit 0, 0 compile errors, 0 warnings** in
`fs/nomount/`. `out/fs/nomount/nomount.o` = 43,272 B.

Build-log assertions from this release:

```
==> KernelSU commits: 4454 -> KSU_VERSION: 35154
-- ReSukiSU version code: 35154
-- ReSukiSU version name: v4.2.0-rc2-6ec8d9a8@ReSukiSU
-- ReSukiSU: using SuSFS Inline hook
-- SUSFS_VERSION: v2.3.0
```

All 7 `susfs_inline` hook checks found (14 hits across the pre-link and post-link
pass); `write_op` and `sel_handle_status_ops` exports found.

### Symbols in the shipped `System.map`

| Check | Result |
|---|---|
| `susfs` symbols | **66** (unchanged from `susfs-4`) |
| NoMount `nomount_*` symbols | **13** |
| NoMount `nm_*` symbols | **33** |
| `nomount_init` | present (`__initcall_165_1706_nomount_init5` — the `fs_initcall`) |
| `nomount_hijacked_lookup` | present |
| `ksu_handle_{setresuid,execveat,execveat_sucompat,post_execveat_sucompat,faccessat,sys_read,stat,sys_reboot,input_handle_event,vfs_fstat}` | each present **exactly once** |
| `CONFIG_KSU_SUSFS_*` in `.config` | all 10 present + `CONFIG_KSU=y`, `CONFIG_KSU_SUSFS=y` |
| `CONFIG_NOMOUNT` | `y` (`out/.config:5344`, and in `autoconf.h`) |
| duplicate symbol definitions at link time | none |

Strings verified in the built `vmlinux`:

* `NoMount: Loaded successfully` / `NoMount: Unloaded successfully`
* `NoMount: Successfully added whiteout rule: %s`
* `NoMount: Successfully added injection rule: %s -> %s`
* `NoMount: Superblock successfully hijacked for dev: 0x%x`
* `NoMount: [ERROR] Failed to register key type (err: %d)`
* the `nomount` key-type name
* `susfs is initialized! version: v2.3.0`
* `v4.2.0-rc2-6ec8d9a8@ReSukiSU`

---

## 4. Artifacts

| File | Size (bytes) | SHA-512 |
|---|---:|---|
| `Zenium-Kernel-RUI4-V1.6-susfs-4-nomount.zip` | 20,630,530 | `b6f9d1e58d88fee0f79f6021db3c2cd50c7488d18dd2d5b312a37dd23fc03a85732388f1804949bbd219ecc173c07c700b02d9e9ba6737e5bfe814c0e70018ab` |
| `Image.gz-dtb` | 18,073,325 | `707359f2a9970297c9fdc4e2af036a0feb1ad9ed4a909e6b04555da556c6522ce269b0442db3f8685b287062db368e4236db345a01a3427af5a59416f2141ff3` |
| `System.map` | 5,629,902 | `4f36971ad584c58eb9fa942ce1780853f5858622c985ed39b89dd9030a15bcc7651dabd051ffa75108d896ffbdc22b97b0d3031917c79ac0efcde84593e0b114` |
| `even_defconfig.config` | — | — |

* Kernel release string: `4.19.325-cip136-st20-Zenium`
* `kernel.string` inside the zip: `Zenium-Kernel-RUI4-V1.6-susfs-4-nomount by DumbDragon`
* Toolchain: Android clang 12.0.5 r416183b, `LLVM=1 LLVM_IAS=1`, `ld.lld`, `-j2`

## 5. Flashing

Targets: `RMX3430`, `RMX3191`, `RMX3193`, `RMX3195`, `RMX3197`, `even`
(Realme C25 / Narzo 50A). Flash `Zenium-Kernel-RUI4-V1.6-susfs-4-nomount.zip` in
AnyKernel3 from a custom recovery — `BLOCK=/dev/block/by-name/boot`,
`IS_SLOT_DEVICE=0`, `do.modules=0`. No modules are shipped (NoMount is built in,
not as an LKM).

## 6. Using NoMount

NoMount is dormant at boot; it registers its key type and nothing else. To drive
it you need the `nm` CLI from
[maxsteeel/nomount/userspace](https://github.com/maxsteeel/nomount/tree/master/userspace).
It is **not** part of this release (it is a userspace binary, and it needs
`CAP_SYS_ADMIN` — build it yourself for arm64 and push it to `/data/local/tmp`).

Typical use:

```
nm add --bind /sdcard/Hidden /data/some/path      # redirect
nm add --inject /system/etc/hosts /sdcard/myhosts # inject content
nm add --whiteout /system/app/Bloatware           # hide
nm list                                             # show active rules
nm del /path                                        # remove one rule
nm clear all                                        # remove everything
```

Rules live in kernel memory only. They are **not** persistent across reboots —
re-apply them after every boot (Magisk boot-script, service.sh, etc.).

---

## 7. Known limitations

* **No on-device runtime test has been performed.** This kernel was verified by
  compile, link, symbol and string inspection only. Neither SUSFS nor NoMount has
  been exercised on real hardware.
* SUSFS and NoMount features are dormant until userspace enables them.
* NoMount rules are volatile (kernel memory only) — see §6.
* If you rebuild from a fresh clone, make sure the `KernelSU` submodule is **not
  shallow**, otherwise `KSU_VERSION` drops to 30701 and the ReSukiSU manager
  refuses to run. `scripts/build_susfs.sh` now hard-fails the build in that case.

---

## Appendix — why the earlier `susfs-4` zip was rejected by the manager

`KernelSU/kernel/Kbuild` computes the version with **no Kconfig override**:

```make
KSU_LOCAL_VERSION := $(shell cd $(KSU_SRC); git rev-list --count HEAD)
KSU_VERSION       := $(shell expr 30000 + $(KSU_LOCAL_VERSION) + 700)
```

A shallow submodule clone (`--depth 1`) made `git rev-list --count HEAD` return
`1`, so `KSU_VERSION = 30000 + 1 + 700 = 30701` — exactly the number the manager
reported. The ReSukiSU manager requires `KSU_VERSION >= 35040` (≥ 4340 commits of
history). Fixed by unshallowing the submodule (commit count 1 → **4454**,
`KSU_VERSION = **35154**`) and by making `scripts/build_susfs.sh` fail the build
when the submodule is shallow or the computed version is below
`${KSU_MIN_VERSION:-35040}`. This class of bug never shows up as a compile error:
the build succeeds, the kernel boots, and userspace rejects it.
