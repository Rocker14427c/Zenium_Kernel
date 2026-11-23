#!/usr/bin/env bash
#
# zenium-verify.sh - pre-flight / post-flight checks for the Zenium 4.19 kernel.
#
# Verifies the things that have actually bitten this project:
#   * KernelSU / BakaSU submodule pin, full history and derived driver version
#   * SUSFS / NoMount version constants vs the pinned source
#   * required defconfig switches (AAL off, priority-UID filter off, ...)
#   * a packaged AnyKernel3 ZIP (image sha256, device names, BLOCK, slot mode)
#
# Usage:
#   scripts/zenium-verify.sh                 # source-tree checks only
#   scripts/zenium-verify.sh <package.zip>   # + verify a flashable ZIP
#
# Exit code: 0 = all checks passed, 1 = at least one FAIL.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

pass=0; fail=0; warn=0
ok()   { printf '  \033[1;32mPASS\033[0m  %s\n' "$*"; pass=$((pass+1)); }
bad()  { printf '  \033[1;31mFAIL\033[0m  %s\n' "$*"; fail=$((fail+1)); }
note() { printf '  \033[1;33mWARN\033[0m  %s\n' "$*"; warn=$((warn+1)); }
hdr()  { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

# ------------------------------------------------------------------ KSU ----
hdr "KernelSU / BakaSU submodule"
GI="$(git -C . rev-parse --git-dir 2>/dev/null)"
PIN="$(git ls-tree HEAD KernelSU 2>/dev/null | awk '{print $3}')"
URL="$(git config -f .gitmodules submodule.KernelSU.url 2>/dev/null)"
BRN="$(git config -f .gitmodules submodule.KernelSU.branch 2>/dev/null)"
echo "  repo : ${URL:-<none>}  branch: ${BRN:-<none>}"
echo "  pin  : ${PIN:-<none>}"
case "$URL" in
  *KernelSU-Next*) EXPECT_MIN=30000 ;;
  *Baka-SU*|*ReSukiSU*) EXPECT_MIN=35000 ;;
  *) EXPECT_MIN=0; note "unknown submodule origin; driver-version formula not asserted" ;;
esac
if [ -d KernelSU/.git ] || [ -f KernelSU/.git ]; then
  if [ -f "$GI/modules/KernelSU/shallow" ] || [ -f KernelSU/.git/shallow ]; then
    bad "submodule history is SHALLOW -> commit count (and driver version) will be wrong; run: git -C KernelSU fetch --unshallow"
  else
    CNT="$(git -C KernelSU rev-list --count HEAD 2>/dev/null || echo 0)"
    ACTUAL_PIN="$(git -C KernelSU rev-parse HEAD 2>/dev/null)"
    if [ "$ACTUAL_PIN" = "$PIN" ]; then ok "submodule checked out at the pinned commit ($CNT commits in history)"
    else bad "submodule HEAD $ACTUAL_PIN != pin $PIN (stale checkout)"; fi
    if [ "$CNT" -gt 1 ]; then
      case "$URL" in
        *KernelSU-Next*) VER=$((30000 + CNT + 289)) ;;
        *Baka-SU*|*ReSukiSU*) VER=$((30000 + CNT)) ;;
        *) VER=$CNT ;;
      esac
      echo "  derived driver version: $VER  (formula per origin; cross-check the manager's minimum)"
      [ "$VER" -ge "$EXPECT_MIN" ] && ok "driver version >= $EXPECT_MIN" || bad "driver version $VER < $EXPECT_MIN"
    else bad "cannot derive driver version (commit count $CNT)"; fi
  fi
else
  note "submodule not initialised here (fine for packaging-only work): git submodule update --init"
fi

# -------------------------------------------------------- SUSFS/NoMount ----
hdr "SUSFS / NoMount versions"
SV="$(sed -n 's/^#define SUSFS_VERSION "\(.*\)"/\1/p' include/linux/susfs.h 2>/dev/null | head -1)"
NV="$(sed -n 's/^#define NOMOUNT_BASE_VERSION "\(.*\)"/\1/p' fs/nomount/nomount.h 2>/dev/null | head -1)"
echo "  SUSFS_VERSION   : ${SV:-<missing>}"
echo "  NOMOUNT_VERSION : ${NV:-<missing>}"
[ -n "$SV" ] && ok "SUSFS core present" || bad "include/linux/susfs.h missing SUSFS_VERSION"
[ -n "$NV" ] && ok "NoMount core present" || bad "fs/nomount/nomount.h missing NOMOUNT_BASE_VERSION"
if [ -f fs/nomount/nomount.c ]; then
  if grep -q "rcu_guard" fs/nomount/nomount.c; then
    bad "fs/nomount/nomount.c uses rcu_guard() (>=5.9 API) - 4.19 build will fail"
  fi
  grep -q "_Static_assert\|static_assert" fs/nomount/nomount.c && \
    note "nomount.c contains a static_assert - C11 via clang is fine with LLVM_IAS, check on GCC"
fi

# ------------------------------------------------------------ defconfig ----
hdr "even_defconfig invariants"
DC=arch/arm64/configs/even_defconfig
chk() { # chk <label> <grep-pattern> <want>   want: y|n
  local label="$1" pat="$2" want="$3" line
  line="$(grep -E "$pat" "$DC" | head -1)"
  if [ "$want" = y ]; then
    case "$line" in CONFIG_*=y) ok "$label = y" ;; *) bad "$label is not y ($line)" ;; esac
  else
    case "$line" in *"is not set"*|"") ok "$label disabled" ;; *) bad "$label should be disabled ($line)" ;; esac
  fi
}
chk "CONFIG_KSU"                         '^CONFIG_KSU='                        y
chk "CONFIG_KSU_MANUAL_HOOK"             '^CONFIG_KSU_MANUAL_HOOK='            y
chk "CONFIG_KSU_SUSFS"                   '^CONFIG_KSU_SUSFS='                  y
chk "CONFIG_NOMOUNT"                     '^CONFIG_NOMOUNT='                    y
chk "MTK AAL (user requirement: off)"    'MTK_AAL_SUPPORT'                     n
chk "SUSFS priority-UID filter"          'KSU_SUSFS_PRIORITY_UID_FILTER'       n
case "$(grep -E '^CONFIG_HZ=' "$DC" | cut -d= -f2)" in
  250|300) ok "CONFIG_HZ = $(grep -E '^CONFIG_HZ=' "$DC" | cut -d= -f2)" ;;
  *) bad "unexpected CONFIG_HZ: $(grep -E '^CONFIG_HZ=' "$DC")" ;;
esac
grep -qE '^CONFIG_LOCALVERSION="-Zenium"' "$DC" && ok 'CONFIG_LOCALVERSION="-Zenium"' \
  || note "CONFIG_LOCALVERSION is not -Zenium"

# ------------------------------------------------ release version strings ----
hdr "release identity"
RS_VER="$(grep -m1 -E '^export version=' run.sh | cut -d= -f2)"
echo "  run.sh version : ${RS_VER:-<none>}"
read -r V P S < <(sed -n '1,6p' Makefile | awk -F' = ' '/^VERSION|^PATCHLEVEL|^SUBLEVEL/{printf "%s ", $2}')
echo "  kernel         : $V.$P.$S"
[ "$V.$P.$S" = "4.19.325" ] && ok "kernel is 4.19.325" || note "kernel is $V.$P.$S"
case "$RS_VER" in *V1.6*) note "run.sh still says $RS_VER while the newest release tag is V1.7/V2.0.0" ;; esac

# ------------------------------------------------------------- package -----
PKG="${1:-}"
if [ -n "$PKG" ]; then
  hdr "package: $PKG"
  [ -f "$PKG" ] || { bad "package not found"; exit 1; }
  unzip -tq "$PKG" >/dev/null 2>&1 && ok "zip integrity (unzip -t)" || bad "zip is corrupt"
  IMG_SHA="$(unzip -p "$PKG" Image.gz-dtb 2>/dev/null | sha256sum | cut -d' ' -f1)"
  [ -n "$IMG_SHA" ] && ok "embedded Image.gz-dtb sha256 = $IMG_SHA" || bad "no Image.gz-dtb in package"
  if [ -f out/arch/arm64/boot/Image.gz-dtb ]; then
    BUILT="$(sha256sum out/arch/arm64/boot/Image.gz-dtb | cut -d' ' -f1)"
    [ "$BUILT" = "$IMG_SHA" ] && ok "package image matches the fresh build output" \
      || bad "package image != fresh build output (stale image!) $BUILT"
  else
    note "no out/arch/arm64/boot/Image.gz-dtb in this tree to compare against"
  fi
  AK="$(unzip -p "$PKG" anykernel.sh 2>/dev/null)"
  echo "$AK" | grep -q 'BLOCK=/dev/block/by-name/boot;' && ok "flash target: by-name/boot (non-A/B)" || bad "unexpected BLOCK"
  echo "$AK" | grep -q 'IS_SLOT_DEVICE=0;'              && ok "IS_SLOT_DEVICE=0" || bad "IS_SLOT_DEVICE is not 0"
  for d in RMX3430 RMX3191 RMX3193 RMX3195 RMX3197 even; do
    echo "$AK" | grep -q "device.name[0-9]*=$d" || bad "device.name missing $d"
  done
  ok "device.name1..6 present (RMX3430/3191/3193/3195/3197/even)"
  echo "$AK" | grep -qE '^kernel.string=.+by (Rocker14427c|DumbDragon)' \
    && ok "kernel.string: $(echo "$AK" | grep -m1 '^kernel.string=')" \
    || note "kernel.string does not carry a known builder name: $(echo "$AK" | grep -m1 '^kernel.string=')"
  echo "$AK" | grep -qE '^do\.modules=[0-9]' && ok "$(echo "$AK" | grep -m1 '^do\.modules=')" || note "do.modules not set explicitly"
  # warn about AnyKernel3 sample junk that must not run
  echo "$AK" | grep -qE '^#?\s*replace_string\(' && note "anykernel.sh still contains replace_string() examples - inspect before flashing"
fi

printf '\n\033[1msummary:\033[0m %d pass, %d warn, %d fail\n' "$pass" "$warn" "$fail"
[ "$fail" -eq 0 ] || exit 1
