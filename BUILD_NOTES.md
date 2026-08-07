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
grep -c nomount out/System.map             # was 32 symbols
ls -l out/arch/arm64/boot/Image.gz-dtb     # 18,112,641 bytes for this build
```

Packed zip appears in repo root: `Zenium-Kernel-Even-RUI4-<yyyymmdd-hhmmss>.zip`.

---

## 8. Sandbox-specific gotchas

- Everything **outside the repo** (toolchains, /home/user/bin, /home/user/tools) is
  **wiped between turns** → re-fetch them every session. The repo itself persists.
- Full build MUST fit one turn (use max timeout).
- Releases: can't upload assets → commit zip to `releases/`, tag it, link
  `https://github.com/Rocker14427c/Zenium_Kernel/raw/arena/019fd813-zenium-kernel/releases/<zip>`.

---

## 9. Applying the NoMount integration to a fresh checkout

Base commit: `897888817` (`rui4-sus`). The patch = commit `89c623771` exactly
(11 files, +1694, **0 deletions**, verified `git apply --check` clean on pristine base,
built, flashed and verified working on-device RMX3430).

```sh
# if raw.githubusercontent.com is blocked, use the API instead:
curl -s -H 'Accept: application/vnd.github.raw' \
  'https://api.github.com/repos/Rocker14427c/Zenium_Kernel/contents/patches/nomount-4.19-even-integration.patch?ref=arena/019fd813-zenium-kernel' \
  -o nomount.patch
git am nomount.patch        # or: git apply nomount.patch
```

NOTE: the OPlus `my_*` partition mount-coverage fix for NoMount is **userspace**
(`/data/adb/modules/nomount/metamount.sh`, on-device), NOT part of this kernel patch.
