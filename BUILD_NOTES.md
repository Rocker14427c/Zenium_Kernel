# BUILD NOTES — compiling Zenium Kernel (even/RUI4) with `run.sh`

Everything below was **actually hit and solved** while building `v1.5-sus` + NoMount
(build artifact `Zenium-Kernel-Even-RUI4-20260807-041348.zip`). Follow it top-to-bottom
and a fresh session/chat can compile without rediscovering the traps.

---

## 0. What `run.sh` expects (do NOT skip)

- Interactive stdin: asks which defconfig → answer `even_defconfig`, then `y`.
- Toolchain: builds with `LD=ld.lld LLVM=1 LLVM_IAS=1` and expects **`./clang` symlink/dir inside the repo**.
- Normal host tools: make, curl, bc, zip(=flex/bison too).
- `chmod 0777 run.sh` (already done in repo).

---

## 1. KernelSU submodule — build dies immediately without it

`drivers/Kconfig:241` sources `drivers/kernelsu/Kconfig`, and `drivers/Makefile:195`
has `obj-$(CONFIG_KSU) += kernelsu/`. KernelSU is an **uninitialized submodule**
in this repo (`KernelSU` → ReSukiSU). Symptom of skipping this:

```
drivers/Kconfig:241: can't open file "drivers/kernelsu/Kconfig"
```

Fix (do this FIRST):

```sh
git submodule update --init KernelSU
ln -sfn ../KernelSU/kernel drivers/kernelsu     # symlink, intentionally untracked
```

---

## 2. Network walls (sandbox) — the root cause of most failures

Only these are reachable: `github.com`, `codeload.github.com`, `api.github.com`.

| Blocked host | What it breaks | Workaround |
|---|---|---|
| `android.googlesource.com` | run.sh's auto-clone of Clang | Pre-seed `./clang` yourself (below) — run.sh then takes the "Clang already exists" path |
| `raw.githubusercontent.com` | raw file downloads | Use blob URLs or the Contents API with `Accept: application/vnd.github.raw` |
| `objects/uploads.githubusercontent.com` | `gh release create --attach` | Commit the zip under `releases/` + tag; link via `.../raw/<branch>/releases/...` |
| distro mirrors / apt | no flex/bison/openssl-dev | Prebuilt toolchains from GitHub (below) |

---

## 3. Clang (expected: clang-r416183b / clang 12.0.5)

```sh
git clone --depth 1 -b 11.0 \
  https://github.com/crdroidandroid/android_prebuilts_clang_host_linux-x86 /home/user/clang
ln -sfn /home/user/clang ./clang        # inside repo root
```

Skip = build starts, dies on compiler probes. Wrong clang (14/17) = LTO/config errors
(`CONFIG_LTO_CLANG=y` pins expectations).

---

## 4. flex / bison / bc (no system package manager)

LineageOS prebuilt build-tools (tarball via codeload — allowed):

```sh
curl -L https://codeload.github.com/LineageOS/android_prebuilts_build-tools/tar.gz/refs/heads/lineage-18.1 \
  -o /tmp/bt.tgz && mkdir -p /home/user/tools && tar -xzf /tmp/bt.tgz -C /home/user/tools
BT=/home/user/tools/android_prebuilts_build-tools-lineage-18.1/linux-x86/bin
export PATH=/home/user/bin:$BT:$PATH
export M4=$BT/m4        # REQUIRED — bison 3.5 aborts without its matching m4
```

`bc`: grab a static `bc-gh` binary from `github.com/gavinhoward/bc` releases,
drop/symlink it as `/home/user/bin/bc`. (kernel's timeconst/Kconfig math needs it)

---

## 5. OpenSSL — the sneakiest failure

`certs/Makefile` runs `scripts/extract-cert certs/signing_key.pem` **during the build**,
linked against system libcrypto (absent here). A stub/fake `libcrypto.a` is NOT enough —
it compiled but the extractor did nothing → cryptic late failure:

```
rm: cannot remove 'certs/signing_key.x509'
```

Fix — build REAL static OpenSSL 1.1.1w from GitHub (~5 min, libs only):

```sh
git clone --depth 1 -b OpenSSL_1_1_1w https://github.com/openssl/openssl /home/user/tools/openssl-src
cd /home/user/tools/openssl-src
./Configure linux-x86_64 no-shared no-zlib no-tests
make -j"$(nproc)" build_libs
```

Then a fake `pkg-config` (kernel build asks pkg-config for libcrypto) at `/home/user/bin/pkg-config`:

```sh
#!/bin/sh
case "$*" in
  *--cflags*) echo "-I/home/user/tools/openssl-src/include" ;;
  *--libs*)   echo "/home/user/tools/openssl-src/libcrypto.a -ldl -lpthread" ;;
  *) exit 0 ;;
esac
```

(`chmod +x` it.) Symptoms gone: `extract-cert` produces a real 1324-byte DER cert.

---

## 6. Launch the build (non-interactive)

```sh
printf "even_defconfig\ny\n" | TERM=xterm \
  PATH=/home/user/bin:$BT:$PATH M4=$BT/m4 \
  bash ./run.sh --choose=1
```

- Give it a long timeout — clean build here took ~15–40 min.
- A trailing `error: Invalid selection` AFTER the zip is produced is HARMLESS
  (run.sh's menu loop hits stdin EOF).

---

## 7. Verify the build actually contains NoMount

```sh
grep CONFIG_NOMOUNT=y out/.config          # must exist
ls out/fs/nomount/nomount.o                # the v2.0.0 driver object
grep -c nm_ out/System.map                 # nm_* symbols come from fs/nomount/
ls -l out/arch/arm64/boot/Image.gz-dtb     # 18,112,641 bytes for this build
```

NoMount **v1.x** lived in `fs/nomount.c` + hooks in `fs/namei.c`, `fs/d_path.c`,
`fs/readdir.c`, `fs/stat.c`, `fs/statfs.c` and `fs/proc/task_mmu.c`. **v2.0.0
dropped all of those in-kernel hooks** — it hijacks `i_op`/`f_op`/`s_op` in RAM
instead and talks to userspace through a keyring payload
(`add_key("nomount", "trigger", ...)`). So a v2 build must show **zero**
`nomount_*` references in those VFS files; only `fs/nomount/` should exist.

Packed zip appears in repo root: `Zenium-Kernel-Even-RUI4-<yyyymmdd-hhmmss>.zip`.

---

## 8. Sandbox-specific gotchas

- Everything **outside the repo** (toolchains, /home/user/bin, /home/user/tools) is
  **wiped between turns** → re-fetch them every session. The repo itself persists.
- Full build MUST fit one turn (use max timeout).
- Releases: can't upload assets → commit zip to `releases/`, tag it, link
  `https://github.com/Rocker14427c/Zenium_Kernel/raw/arena/019fd813-zenium-kernel/releases/<zip>`.

---

## 9. NoMount v2.0.0 integration (now in-tree — no patch needed)

NoMount is vendored directly at `fs/nomount/`, so there is nothing to apply.
It is byte-identical to `kernel/src/` at upstream tag **v2.0.0**
(`b8d268353b4e7ecc53c67d1816a626b7d6579201`), and the build wiring is what
upstream's `kernel/setup.sh` would generate:

```
fs/Kconfig    -> source "fs/nomount/Kconfig"   (before the closing endmenu)
fs/Makefile   -> obj-$(CONFIG_NOMOUNT) += nomount/
even_defconfig-> CONFIG_NOMOUNT=y              (built in, not LKM)
```

Requires `CONFIG_KEYS=y` and `CONFIG_SRCU=y` — both already set in
`even_defconfig`.

With `CONFIG_NOMOUNT=y` the driver is built in, so the module's
`customize.sh`/`metamount.sh` take the *Built-in* path and never try to load an
LKM. Verify support from userspace with `nm version`.

To re-sync to a newer upstream tag later:

```sh
git clone --depth 1 -b <tag> https://github.com/maxsteeel/nomount /tmp/nm
cp -f /tmp/nm/kernel/src/{nomount.c,nomount.h,Kconfig,Makefile} fs/nomount/
```

The superseded v1 integration patch (`patches/nomount-4.19-even-integration.patch`,
commit `89c623771`) was removed along with this change — it no longer applies,
and its VFS hooks are exactly what v2.0.0 got rid of.

NOTE: the OPlus `my_*` partition mount-coverage fix for NoMount is **userspace**
(`/data/adb/modules/nomount/metamount.sh`, on-device), NOT part of this kernel.

---

## 10. ReSukiSU <-> SUSFS kernel-side contract (link-time only!)

ReSukiSU from `v4.2.0-rc1-54-g9d0ff6ae` onwards calls four SUSFS helpers that
**this kernel tree must provide**. They live in `include/linux/susfs_def.h` as
`static inline`, so if they are missing the calls in
`KernelSU/kernel/hook/setuid_hook.c` become *implicit function declarations* —
clang 12 only warns, so **every object compiles fine** and the failure shows up
exclusively at the `vmlinux` link:

```
ld.lld: error: undefined symbol: susfs_set_current_proc_no_su
ld.lld: error: undefined symbol: susfs_is_current_proc_no_su
ld.lld: error: undefined symbol: susfs_clear_current_proc_no_su
ld.lld: error: undefined symbol: susfs_set_current_proc_umounted_for_zygote_next
```

`make drivers/kernelsu/` will NOT catch this — you have to link vmlinux.

Required in `include/linux/susfs_def.h` (bit numbers match upstream susfs4ksu):

```c
#define TIF_PROC_UMOUNTED                 33
#define TIF_PROC_NO_SU                    34
#define TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT 35

susfs_{is,set,clear}_current_proc_umounted()
susfs_{is,set,clear}_current_proc_umounted_for_zygote_next()
susfs_{is,set,clear}_current_proc_no_su()
susfs_is_current_proc_umounted_app()
```

arm64 in this 4.19 tree only uses TIF bits 0-26 (`arch/arm64/include/asm/
thread_info.h`), so 33-35 are free. Before picking new bits, re-check that:

```sh
grep -rhoE '#define\s+TIF_[A-Z0-9_]+\s+[0-9]+' arch/arm64 include/linux/susfs_def.h
```

After bumping the ReSukiSU submodule, always confirm the kernel side still
satisfies it before shipping:

```sh
# every susfs_* ReSukiSU calls, minus every susfs_* defined anywhere
# NOTE: git grep does NOT descend into submodules, so collect both sides.
cd KernelSU && git grep -hoE '\bsusfs_[a-z0-9_]+\s*\(' -- kernel | tr -d ' (' | sort -u > /tmp/want
( cd .. && git grep -hoE '\bsusfs_[a-z0-9_]+\s*\(' -- ':!Documentation' ':!android'
  cd KernelSU && git grep -hoE '\bsusfs_[a-z0-9_]+\s*\(' -- kernel
) | tr -d ' (' | sort -u > /tmp/have
comm -23 /tmp/want /tmp/have      # must print nothing
```

Anything printed there is defined nowhere, so it is a link error waiting to
happen — add it to `include/linux/susfs_def.h` (or the matching `fs/susfs.c`
section) before shipping.

---

## 11. DO NOT bump ReSukiSU to 9d0ff6ae (or newer) — it bootloops

**Confirmed on hardware.** `9d0ff6ae` boots to the splash screen and panics
within 2-3 seconds, then reboots in a loop. `88dbc786` boots fine, with
NoMount v2.0.0 and SUSFS working (KSU_VERSION 35040).

This was a clean controlled experiment. The two builds differ by exactly one
line of source:

```
$ git diff --stat defe58f906cf d2f025adf01f
 KernelSU | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

and the configs extracted out of the two shipped `Image.gz-dtb` files are
**identical — 0 differing lines**. The only other deltas are two strings that
cannot fault (`LOCALVERSION` gained `-Even`, and `KBUILD_COMPILER_STRING`).
So the KernelSU commit is the cause, not the build.

### What the build warns about

`9d0ff6ae` is not an incremental bump over `88dbc786` — it is 374 files and
+38008 lines, including new arm64 runtime kernel-text scanning
(`scan_call_to()` in `kernel/hook/arm64/patch_memory.c`).

Its own build-time check, `kernel/tools/inline_hook_check.mk`, scans *this*
kernel tree and prints:

```
susfs_inline: WARNING: Detected KSU_MANUAL_HOOK guard in <file>
susfs_inline: WARNING: Your build maybe broken.
```

Five of the seven hook sites here still carry the legacy
`CONFIG_KSU_MANUAL_HOOK` guard:

| File | `CONFIG_KSU_MANUAL_HOOK` hits |
|---|---|
| `kernel/sys.c` | 2 |
| `fs/exec.c` | 3 |
| `fs/open.c` | 2 |
| `fs/stat.c` | 6 |
| `kernel/reboot.c` | 2 |
| `fs/read_write.c` | 0 (already migrated) |
| `drivers/input/input.c` | 0 (already migrated) |

### The exact faulting mechanism is NOT established

Do not repeat the earlier mistake of treating the warning above as the cause.
It was checked and does not hold up:

- `9d0ff6ae` defines only two relevant static keys —
  `ksu_is_init_rc_hook_enabled` and `ksu_is_input_hook_enabled`
  (`kernel/runtime/ksud_integration.c:99-100`) — and those are exactly the two
  sites in this tree that are *already* migrated.
- There is **no** static key for `setresuid`, `execveat`, `faccessat`, `stat` or
  `sys_reboot`. All five handlers still exist in `9d0ff6ae` and their signatures
  match this tree's call sites (verified against `sucompat.c`/`sucompat.h`).

So the five legacy sites have nothing to migrate *to* and are not obviously
broken. `check_ksu_manual_guard` only greps for the literal string
`CONFIG_KSU_MANUAL_HOOK`; it is a heuristic smell, not proof.

Also checked and ruled out as an obvious cause: the new `scan_call_to()` in
`kernel/hook/arm64/patch_memory.c` is called from exactly one place,
`kernel/policy/app_profile.c:292`, as a read-only feature probe — not from
sucompat init.

What is *proven* is the A/B result above. What is *not* known is which line of
`9d0ff6ae` faults. `CONFIG_PANIC_ON_OOPS=y` + `CONFIG_PANIC_TIMEOUT=1` turn it
into an instant reboot loop with no visible output, and there is no pstore log
on this device, so the fault was never observed directly.

### Cross-check against every released tag

| Release | `include/linux/susfs_def.h` | KernelSU |
|---|---|---|
| `v1.5.2-clang12-20260903-152024` | ABSENT | `9d0ff6ae` |
| `v1.5.2-20260903` | ABSENT | `88dbc786` |
| `v1.5.1-experimental-20260815` | PRESENT | `88dbc786` |
| `v1.5-sus-nomount-20260807` | PRESENT | `88dbc786` |

`9d0ff6ae` has only ever shipped with SUSFS **disabled**. Every tag carrying
this SUSFS v2.2.0 port ships `88dbc786`. Bumping the gitlink is the first time
the two were ever combined, which is why nothing upstream caught it.

### To re-attempt the bump

Since the faulting mechanism is unknown, **bisect ReSukiSU's own history**
between `88dbc786` and `9d0ff6ae` rather than guessing at a port:

1. Build a variant with `CONFIG_PANIC_TIMEOUT=0` and `CONFIG_PANIC_ON_OOPS=n` so
   a fault halts with the trace on screen instead of rebooting. Without this
   every test costs a reflash and yields no information.
2. Bisect the submodule between the two commits. `9d0ff6ae` is 374 files and
   +38008 lines over `88dbc786`, so a few steps should localise it.
3. `susfs_def.h` already provides the four helpers `9d0ff6ae` needs
   (`susfs_{is,set,clear}_current_proc_no_su`,
   `susfs_set_current_proc_umounted_for_zygote_next`) — see section 10. That
   part is done and correct regardless.
4. Flash each candidate **on its own**, not bundled with other changes.

Do not re-bump the gitlink on its own and assume the `inline_hook_check.mk`
warning is the blocker.

### No pstore log is available on this device

`CONFIG_PSTORE_RAM=y` and `CONFIG_PSTORE_CONSOLE=y` are set, but **none of the
five appended DTBs contains a `ramoops` node**, and `CONFIG_MTK_AEE_FEATURE` is
not set. So `/sys/fs/pstore/` stays empty and there is no captured panic.

To make a crashing kernel show its fault on screen instead of rebooting, build
with `CONFIG_PANIC_TIMEOUT=0` and `CONFIG_PANIC_ON_OOPS=n`.
