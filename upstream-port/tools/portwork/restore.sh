#!/bin/bash
# restore.sh - recreate the v5.15.220 build environment inside a sandbox whose only egress is
# GitHub + PyPI (kernel.org, deb.debian.org, ftp.debian.org, archive.ubuntu.com and
# objects.githubusercontent.com all time out here; measured 2026-09-05).
#
# Deliberate choices, each because of a measurement:
#  * base tree  = shallow clone of gregkh/linux at tag v5.15.220, because stable releases are not
#    tagged in torvalds/linux, and a shallow clone gives a real git object store so that `git am`,
#    `git diff --numstat v5.15.220..HEAD` and the packaging gates all keep working (the tarball
#    route would need a 1.4 GB `git add` of the whole tree first).
#  * host tools = LineageOS/android_prebuilts_build-tools (bison, flex, m4, bc). apt is dead
#    (no sources.list, mirrors unreachable) and GitHub *release assets* are unreachable because
#    they 302 to objects.githubusercontent.com, which times out; codeload tarballs do not.
#  * cross gcc  = LineageOS mirror of the AOSP aarch64-linux-gnu 9.3 prebuilt (glibc, 120 MB),
#    matching what the last successful build used: report/build.json's toolchain record lists
#    clang-14 as unusable and the build ran on the "S6 toolchain wrapper" + host gcc.
#  * dtc        = built from the kernel tree's own scripts/dtc (no dtc prebuilt in build-tools),
#    which is what the earlier DTB gates used.
set -o pipefail
ROOT=/home/user/portwork
LOG=$ROOT/logs/restore.log
REPO=/home/user/Zenium_Kernel
mkdir -p "$ROOT"/{ref,out,configs,logs,tools,dl}
exec > >(tee -a "$LOG") 2>&1
say(){ printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }

say "== [1/5] host tools: bison / flex / m4 / bc =="
if [ ! -x "$ROOT/tools/build-tools/bin/bison" ]; then
  [ -f "$ROOT/dl/bt.tar.gz" ] || { say "downloading build-tools"; curl -fsSL --retry 3 -o "$ROOT/dl/bt.tar.gz" \
    https://codeload.github.com/LineageOS/android_prebuilts_build-tools/tar.gz/refs/heads/lineage-21.0; }
  say "extracting ($(du -h "$ROOT/dl/bt.tar.gz" | cut -f1))"
  rm -rf "$ROOT/dl/bt" && mkdir -p "$ROOT/dl/bt"
  tar -xzf "$ROOT/dl/bt.tar.gz" -C "$ROOT/dl/bt" --strip-components=1
  src=""
  for c in "$ROOT/dl/bt/linux-x86" "$ROOT/dl/bt"/*/linux-x86; do [ -d "$c/bin" ] && src="$c" && break; done
  [ -n "$src" ] || { say "FATAL: no linux-x86/bin inside build-tools"; exit 1; }
  mkdir -p "$ROOT/tools/build-tools"
  cp -a "$src/bin" "$ROOT/tools/build-tools/bin"
  [ -d "$src/common" ] && cp -a "$src/common" "$ROOT/tools/build-tools/common"
  [ -d "$src/lib64" ] && cp -a "$src/lib64" "$ROOT/tools/build-tools/lib64"
  ls -la "$ROOT/dl/bt" | head -8
fi
for t in bison flex m4 bc gavinhoward-bc make ld; do
  p="$ROOT/tools/build-tools/bin/$t"; [ -x "$p" ] && say "  tool $t -> $("$p" --version 2>&1 | head -1)" || say "  tool $t MISSING"
done

say "== [2/5] cross toolchain: buildroot-flavoured aarch64 gcc 9.3 =="
if [ ! -x "$ROOT/tools/gcc/bin/aarch64-buildroot-linux-gnu-gcc" ] && \
   [ ! -x "$ROOT/tools/gcc/bin/aarch64-linux-gnu-gcc" ]; then
  [ -f "$ROOT/dl/gcc.tar.gz" ] || { say "downloading gcc prebuilt"; curl -fsSL --retry 3 -o "$ROOT/dl/gcc.tar.gz" \
    https://codeload.github.com/LineageOS/android_prebuilts_gcc_linux-x86_aarch64_aarch64-linux-gnu-9.3/tar.gz/refs/heads/lineage-23.2; }
  say "extracting ($(du -h "$ROOT/dl/gcc.tar.gz" | cut -f1))"
  rm -rf "$ROOT/dl/gcc" && mkdir -p "$ROOT/dl/gcc"
  tar -xzf "$ROOT/dl/gcc.tar.gz" -C "$ROOT/dl/gcc" --strip-components=1
  mv "$ROOT/dl/gcc" "$ROOT/tools/gcc"
  # This SDK is a relocated buildroot tree: its toolchain-wrapper symlinks resolve .br_real
  # binaries relative to bin/, and relocate-sdk.sh wants coreutils' `file`, which this sandbox
  # has no way to install (apt is dead). Skip it and prove the compiler instead - an -c compile
  # whose readelf header says AArch64 is the only evidence that matters.
fi
GBIN=$(for c in "$ROOT/tools/gcc/bin" "$ROOT"/tools/gcc/*/bin; do [ -x "$c/aarch64-buildroot-linux-gnu-gcc" ] && echo "$c" && break; done)
[ -n "$GBIN" ] || GBIN=$(for c in "$ROOT/tools/gcc/bin" "$ROOT"/tools/gcc/*/bin; do ls "$c"/*-gcc >/dev/null 2>&1 && echo "$c" && break; done)
if [ -n "$GBIN" ]; then
  drv=$(basename "$(ls "$GBIN"/*-gcc | head -1)"); pfx=${drv%-gcc}
  printf 'int main(void){return 0;}\n' > /tmp/gcc-probe.c
  "$GBIN/$pfx-gcc" -c -o /tmp/gcc-probe.o /tmp/gcc-probe.c && \
    say "  ok: $pfx-gcc ($(  "$GBIN/$pfx-gcc" --version | head -1 )) -c -> ELF $(head -c 20 /tmp/gcc-probe.o | od -An -tx1 | tr -s ' ' | cut -c1-40)"
  "$GBIN/$pfx-ld" --version 2>/dev/null | head -1 | sed 's/^/  linker: /'
  "$GBIN/$pfx-readelf" -h /tmp/gcc-probe.o 2>/dev/null | grep -E 'Machine|Class' | sed 's/^/    /'
else
  say "  FATAL: no cross driver under $ROOT/tools/gcc"
fi
say "  bc: $(bc --version 2>/dev/null | head -1)"; [ -x "$ROOT/tools/build-tools/bin/bc" ] || ln -sf gavinhoward-bc "$ROOT/tools/build-tools/bin/bc"

say "== [3/5] base tree: shallow clone of gregkh/linux @ v5.15.220 =="
if [ ! -d "$ROOT/ref/linux/.git" ]; then
  say "cloning (depth 1, single tag)"
  git clone --quiet --depth 1 --branch v5.15.220 https://github.com/gregkh/linux.git "$ROOT/ref/linux"
else
  say "already present"
fi
cd "$ROOT/ref/linux" || exit 1
git -c advice.detachedHead=false checkout -q v5.15.220 2>/dev/null || true
say "  base commit: $(git rev-parse --short HEAD)  describe: $(git describe --tags 2>/dev/null)"
grep -m1 '^VERSION\|^PATCHLEVEL\|^SUBLEVEL\|^EXTRAVERSION' Makefile | tr '\n' ' '; echo
say "  tree size: $(du -sh . 2>/dev/null | cut -f1)"

say "== [4/5] env.sh: what every later gate sources =="
[ -f "$ROOT/tools/env.sh" ] || say "  FATAL: tools/env.sh missing (write it first)"
. "$ROOT/tools/env.sh"
say "  bison: $(command -v bison)"; say "  flex: $(command -v flex)"; say "  bc: $(command -v bc)"
say "  prefix: $CROSS_COMPILE"; say "  gcc: $(command -v ${CROSS_COMPILE}gcc)"; "${CROSS_COMPILE}gcc" --version 2>&1 | head -1

say "== [5/5] series tree: git am the 82 published patches onto the base =="
if [ ! -d "$ROOT/series/.git" ]; then
  git -c advice.detachedHead=false worktree add --detach "$ROOT/series" HEAD 2>/dev/null || {
    say "  worktree add failed; falling back to a local clone"
    git clone --quiet --no-hardlinks "$ROOT/ref/linux" "$ROOT/series"; }
fi
cd "$ROOT/series" || exit 1
git -c advice.detachedHead=false checkout -q --detach HEAD
git config user.name "Zenium Port"; git config user.email "port@zenium.invalid"
have=$(git rev-list --count HEAD 2>/dev/null); say "  series HEAD: $(git rev-parse --short HEAD) (commits: $have)"
say "  applying $REPO/upstream-port/patch-series/*.eml"
git am -q $(ls "$REPO"/upstream-port/patch-series/*.eml | grep -v cover | sort) 2>&1 | tail -12
# the cover letter has no diff body, so `git am` on the raw glob dies with "Patch is empty."
say "  after am: HEAD=$(git rev-parse --short HEAD) commits=$(git rev-list --count HEAD) dirty=$(git status --porcelain | wc -l)"
say "  series tree: $(git rev-parse HEAD^{tree})"
say "  numstat vs base: $(git diff --shortstat v5.15.220..HEAD 2>/dev/null || git diff --shortstat "$(cd "$ROOT/ref/linux" && git rev-parse HEAD)"..HEAD)"
say "RESTORE_DONE rc=$?"
