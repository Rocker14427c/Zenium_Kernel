# Zenium Kernel RUI4 — V1.7 (BakaSU + NoMount 2.1)

Built from branch `arena/01a0eb93-zenium-kernel`, on top of the Round-7 baseline
`689605bd` (`even: flashlights: increase torch brightness levels from 5 to 7`).

* **Kernel:** `4.19.325-cip136-st20-Zenium`
* **Root manager:** BakaSU (formerly ReSukiSU) `v4.2.0-rc3-5b76b884@BakaSU`
* **SUSFS:** **v2.3.0 — unchanged, exactly as you asked**
* **NoMount:** **v2.1.0** (was v2.0.0)
* **Build:** rc=0, **0 errors**, 0 warnings from any SUSFS / NoMount / BakaSU code
* **Flashable via AnyKernel3** — `boot` partition only (`IS_SLOT_DEVICE=0`)

Devices: RMX3430, RMX3191, RMX3193, RMX3195, RMX3197, `even`.

---

## 1. What changed

### 1.1 ReSukiSU → BakaSU (the rename is official)

You were right: the ReSukiSU developer renamed the project. GitHub now redirects
`ReSukiSU/ReSukiSU` → `Baka-SU/BakaSU`; both URLs resolve to the same repository
(`full_name: Baka-SU/BakaSU`). The rename commit is `97c102ba`
*"treewide: rename project (#461)"*, which also changed the internal package name
from `com.resukisu.resukisu` to `org.bakasu.bakasu` and dropped multi-manager
support for MKSU / RKSU / SukiSU-Ultra.

The `KernelSU` submodule moved from ReSukiSU `6ec8d9a8a8be` to BakaSU **`5b76b884c75f`**.

**Why `5b76b884` and not BakaSU `main` (`f4435f00`)?** Because BakaSU `main`
**deliberately breaks SUSFS builds**. Commit `48fa4bb7` *"kernel: suspend susfs
build"* adds an unconditional hard error to `kernel/tools/susfs_compat.mk`:

```make
$(info -- BakaSU: susfs has NOT update with latest KernelSU source)
$(info -- BakaSU: Please wait simonpunk update)
$(error Please wait susfs update.)
```

`kernel/Kbuild` includes that file whenever `CONFIG_KSU_SUSFS=y`, so on `main`
**the kernel build fails outright**. `5b76b884` is the *parent* of that commit —
the newest BakaSU that still officially supports SUSFS, and it already contains
the rename plus every kernel fix since. Only three commits are left behind
(`48fa4bb7` itself, a Rust dependency bump, and the manager translations), none
of which affect this kernel.

### 1.2 NoMount v2.0.0 → v2.1.0

`fs/nomount/` was replaced with the v2.1.0 sources (`c7f63e3feb41`, 2026-10-06).
All four files are **byte-identical to upstream** (sha256-verified):

| file | v2.0.0 | v2.1.0 |
|---|---|---|
| `Kconfig` | 234 B | 234 B (identical) |
| `Makefile` | 117 B | 339 B |
| `nomount.c` | 62,149 B | 63,004 B |
| `nomount.h` | 11,840 B | 11,575 B |

Notable v2.1.0 changes, all memory-safety work:

* `nomount_hijacked_drop_inode` / `nomount_hijacked_evict_inode` wired into
  `fake_sop.drop_inode` / `.evict_inode` — fixes use-after-free and double-free
  on inode eviction.
* `nm_dir_ops` merges the old separate `nm_iop` + `nm_fop` into one struct holding
  `fake_iop`, `fake_fop`, `orig_iop`, `orig_fop`, `dir_node` and `rcu_head`.
* `struct nm_inode_info` drops `r_path`/`flags` and gains `rule` + `rcu`.
* `nomount_rules_ht` renamed to `nomount_leaves_ht`.
* `igrab()` `-ESTALE` handling and lockless dir-node eviction races fixed.
* `Makefile` now derives a commit count from git; harmless in an in-tree build
  (see §4).

**The three kernel integration lines did not change at all** — see §2.

---

## 2. Your question: "isn't there an easy method where I don't have to patch the kernel?"

Short answer: **not on this kernel, and the reason is a hard technical limit, not
something I can engineer around.** But you also don't need it — see the second
half.

### 2.1 Why the GKI method doesn't apply to you

The NoMount README's easy path (Method 2, the prebuilt LKM) is **GKI-only**. It
works on a GKI 5.10+ kernel because the KMI is stable, so one `.ko` loads
everywhere. Your kernel is **4.19 non-GKI**, and the README says so explicitly:
legacy kernels must integrate into the kernel source.

Your kernel is doubly locked down:

* `CONFIG_MODVERSIONS=y` — every imported symbol carries a CRC of the *exact*
  prototype. A `.ko` built against any other tree is rejected on load.
* `CONFIG_MODULE_SIG=y`, `CONFIG_MODULE_SIG_FORCE=y`, `CONFIG_MODULE_SIG_SHA512`
  **and** `CONFIG_SYSTEM_TRUSTED_KEYS=""` — signature checking is enforced
  (`sig_enforce = IS_ENABLED(CONFIG_MODULE_SIG_FORCE)`) while the system trusted
  keyring is **empty**, so `verify_pkcs7_signature()` can never succeed.
  *No loadable module of any kind can load on this kernel*, signed or not.

I confirmed this kernel builds **zero modules** — `make modules` produces nothing,
and the previous AnyKernel3 zip has `do.modules=0`.

### 2.2 What the module path would actually cost

I did check whether `CONFIG_NOMOUNT=m` is even possible, because you asked:

* NoMount's `Kconfig` is `tristate`, so it *can* build as a module. ✔
* `include/linux/module.h` (4.19) maps `fs_initcall(fn) → module_init(fn)` under
  `#ifdef MODULE`, so the module gets a real `init_module` entry point. ✔
* NoMount's superblock hijack happens in `nomount_generate_virtual_topology()`,
  the **rule-add path** — *not* in a mount hook — so it does not need to be
  built-in to work. ✔

So it is buildable. But shipping it would require **either** relaxing
`CONFIG_MODULE_SIG_FORCE` (weakening the kernel's security posture) **or**
embedding a new trusted key and rebuilding the kernel once anyway — plus
injecting the `.ko` into the boot ramdisk via `ramdisk/lib/modules/` and a
`modules.load` entry, which changes the boot image. That is exactly the
"breaking or compromising functionalities" you told me to avoid, and it buys you
a module you'd still have to rebuild against *this* kernel every time.

### 2.3 What you actually have today — and it already is the easy method

**You never patch the kernel. I do, once, and it is three lines in three files
that have not changed across either NoMount version:**

```
fs/Kconfig:331      source "fs/nomount/Kconfig"
fs/Makefile:19      obj-$(CONFIG_NOMOUNT)          += nomount/
even_defconfig:5114 CONFIG_NOMOUNT=y
```

Everything else lives in `fs/nomount/`, and I keep those four files
**byte-identical to upstream** precisely so that an update is a pure four-file
swap with no merge, no `.rej`, no hand-editing. That is what this release is:
`git show v2.1.0:kernel/src/<f> > fs/nomount/<f>` — verified by sha256 above.
Nothing else in the kernel tree was touched for NoMount.

So the update cost is on **my** side, not yours: you flash a zip. The only thing
a NoMount update forces is one kernel rebuild here, which is a few minutes of
machine time and zero risk to your phone.

---

## 3. Verification performed on this build

| check | result |
|---|---|
| build exit code | **0** |
| compile errors | **0** |
| warnings from SUSFS / NoMount / BakaSU | **0** (all 74 warnings are pre-existing vendor/Oplus/MTK code; every file I hook has 0) |
| `BakaSU/susfs_inline` hook checks | **14/14 pass** (`setresuid`, `execveat`, `faccessat`, `sys_read`, `stat`, `sys_reboot`, `input_handle_event`, ×2 runs) |
| `KSU_VERSION` | **35222** (BakaSU commits 4522; manager minimum is 35040) |
| version string in image | `v4.2.0-rc3-5b76b884@BakaSU` |
| `ReSukiSU` strings in image | **0** |
| `TAGLMK` strings / config | **0** |
| SUSFS banner in image | `susfs is initialized! version: v2.3.0` |
| NoMount banner in image | `NoMount: Loaded successfully` |
| NoMount version | `21` (base) |
| `susfs_*` symbols | 65 unique, incl. `susfs_init`, `susfs_ksu_sid`, `susfs_priv_app_sid` |
| `nomount_*` symbols | 13, incl. **`nomount_hijacked_drop_inode`** and **`nomount_hijacked_evict_inode`** (new in v2.1.0) |
| `nm_*` symbols | 41 |
| `nomount_leaves_ht` (v2.1.0 rename) | present |
| the 10 SUSFS hooks in `System.map` | each exactly **once** |
| `CONFIG_NOMOUNT` / `CONFIG_KSU` / `CONFIG_KSU_SUSFS` | `y` / `y` / `y` |
| `CONFIG_KSU_MANUAL_HOOK` / `CONFIG_KSU_TRACEPOINT_HOOK` | not set → **SUSFS inline hook is the active method** |
| all 9 `CONFIG_KSU_SUSFS_*` sub-features | `y` |
| `Image.gz-dtb` | 18,074,579 B |

Coexistence is unchanged and by design: NoMount hijacks VFS `i_op`/`d_op`/`s_op`
reversibly (originals saved as `orig_iop`, `orig_dops`, `orig_fop`, `orig_sop`,
`orig_xattr`), while SUSFS uses inline hooks. Different mechanisms, no symbol
collision — `nomount_*`/`nm_*` vs `susfs_*` vs `ksu_*`. NoMount's control plane
is its own kernel key type `"nomount"` (`nm_key_preparse`, needs `CAP_SYS_ADMIN`)
and has no KernelSU coupling; `grep -rin nomount KernelSU/` returns zero hits.

---

## 4. Known cosmetic quirk

NoMount v2.1.0's `Makefile` derives `NOMOUNT_COMMIT_COUNT` from
`git -C fs/nomount rev-list --count HEAD`. In an **in-tree** build `fs/nomount`
sits inside the kernel repository, so that resolves to the *kernel's* commit
count (815083) and the version string reads `21-815083` instead of a NoMount
commit count. It is log-only and harmless. I deliberately left the upstream file
unmodified so that future NoMount updates remain a clean four-file swap (§2.3).

---

## 5. Flash instructions

1. Copy `Zenium-Kernel-RUI4-V1.7-susfs-4-bakasu-nomount-2.1.zip` to the phone.
2. Reboot to recovery (or use the KernelSU/BakaSU manager's "Install" → "Select
   a file to flash" if you have a recovery-less setup).
3. Flash the zip. It patches `boot` only; `IS_SLOT_DEVICE=0`.
4. Reboot. First boot takes a little longer than usual.

No wipe is needed. NoMagisk modules need to be reinstalled.

**If anything goes wrong:** the previous known-good build is still published as
release `susfs-4` (commit `689605bd`) — flash that to go back.
