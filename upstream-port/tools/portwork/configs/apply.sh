#!/bin/bash
# apply.sh - reproduce the recorded 5.15 config state for this series, WITHOUT re-running
# ./build.sh configure (forbidden on a hand-configured tree: it once regenerated .config from
# defconfig and silently lost MACH_MT6768, hence PINCTRL_MT6768/MTK_DEVAPC, COMMON_CLK_MT6768, the
# AUXADC pair, RTC_DRV_MT6397 and BUILD_ARM64_APPENDED_DTB_IMAGE -> Image 27,015,176 with no DTB
# appended at all; rejected as build-37a, kept in portwork/logs/build-37a-rejected.log upstream).
#
# Recipe as recorded in upstream-port/report/build.json gates.config_recipe: set the named symbols,
# olddefconfig, then FAIL if any is missing. The two in-repo fragments (upstream-port/dev/*.fragment)
# are merged too, so board options come from the repo rather than from a lost editor session.
#
# Two names were removed from SYMS after measuring: gates.config_recipe in build.json lists
# APPENDED_DTB_IMAGE_NAMES and APPENDED_DTBO_IMAGE_NAMES, but `grep -rl "config <name>$"
# arch/*/Kconfig init/Kconfig` finds no such symbol in v5.15.220+series and
# ./scripts/config --state returns "undef" for both. They are 4.19 vendor names; on this tree the
# arm64 equivalent is BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES (set to "mediatek/mt6768" by
# dev/even.fragment, verified present), and there is no DTBO Kconfig symbol at all - dtbo.img is
# produced by the host tool upstream-port/bin/mkdtboimg.py, never by Kconfig. Keeping the two
# phantom names would make a correct tree fail this gate forever.
#
# Quote handling in the fragment merge matters: the fragment line already carries the quotes
# (CONFIG_..._NAMES="mediatek/mt6768") and `scripts/config --set-str` re-quotes, which produced
# CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES="\"mediatek/mt6768\"" - a literal-quoted path that
# would match no DTB and silently append nothing. Values are therefore unquoted before --set-str.
# SYSTEM_TRUSTED_KEYRING (not just SYSTEM_TRUSTED_KEYS) is what actually gates scripts/extract-cert.
#
# One recorded deviation from the original: this sandbox has no libssl-dev and no way to get it
# (apt has no sources, mirrors unreachable), so scripts/extract-cert cannot build and `make prepare`
# dies on the host-tool step. Disabling the module-signing / platform-keyring options is the
# minimal unblock and touches nothing in the display path.
set -o pipefail
. /home/user/portwork/tools/env.sh
TREE=${TREE:-/home/user/portwork/series}
REPO=${REPO:-/home/user/Zenium_Kernel}
FRAG_DIR="$REPO/upstream-port/dev"
SYMS="MACH_MT6768 PINCTRL_MT6768 COMMON_CLK_MT6768 MTK_DEVAPC MEDIATEK_MT6577_AUXADC MT635X_AUXADC RTC_DRV_MT6397 MTK_PMIC_WRAP MFD_MT6397 REGULATOR_MT6358 MTK_SMI_EXT MTK_M4U MTK_DISP_M4U BUILD_ARM64_APPENDED_DTB_IMAGE BUILD_ARM64_APPENDED_DTB_IMAGE_NAMES"
cd "$TREE" || exit 1
[ -f .config ] || { echo "apply.sh: no .config - run 'make ARCH=arm64 defconfig' first"; exit 2; }
for s in $SYMS; do
  case "$s" in
    *_NAMES) ;;
    *) echo "  enable  $s"; ./scripts/config --enable "$s" ;;
  esac
done
for s in SYSTEM_TRUSTED_KEYRING MODULE_SIG MODULE_SIG_ALL MODULE_SIG_FORCE SYSTEM_DATA_VERIFICATION_KEY INTEGRITY_PLATFORM_KEYRING INTEGRITY_ASYMMETRIC_KEYS IMA; do ./scripts/config --disable "$s"; done
# Causal chain measured here, not guessed: scripts/Makefile:15 puts extract-cert in
# hostprogs-always-$(CONFIG_SYSTEM_TRUSTED_KEYRING); SYSTEM_TRUSTED_KEYRING is selected by
# SYSTEM_DATA_VERIFICATION (init/Kconfig:2076-2078), which is selected by
# CFG80211_REQUIRE_SIGNED_REGDB (net/wireless/Kconfig:92-95, hidden-but-default-y under
# CONFIG_CFG80211, so scripts/config cannot clear it while CFG80211 is on). Therefore CFG80211
# itself must go, then SYSTEM_TRUSTED_KEYRING can be disabled by hand because nothing selects it
# any more. Order matters: doing it the other way leaves the value stale in .config and prepare
# keeps failing on openssl/bio.h.
./scripts/config --disable CFG80211 --disable MAC80211
./scripts/config --disable SYSTEM_TRUSTED_KEYRING --disable SYSTEM_REVOCATION_LIST --disable SYSTEM_EXTRA_CERTIFICATE
# The CMDQ mailbox driver is the mainline side of the L1 boundary; without it the tree cannot even
# build drivers/mailbox/mtk-cmdq-mailbox.o, which is the cheapest real compile of that header's
# consumer.
./scripts/config --enable MAILBOX --enable MTK_CMDQ_MBOX
for s in SYSTEM_TRUSTED_KEYS MODULE_SIG_KEY SYSTEM_REVOCATION_KEYS; do ./scripts/config --set-str "$s" ""; done
for f in even.fragment even-hardware.fragment; do
  [ -f "$FRAG_DIR/$f" ] || continue
  echo "  merge   $FRAG_DIR/$f"
  while read -r line; do
    case "$line" in
      CONFIG_*=y) ./scripts/config --enable "${line%%=*}" ;;
      CONFIG_*=n) ./scripts/config --disable "${line%%=*}" ;;
      CONFIG_*=*) ./scripts/config --set-str "${line%%=*}" "$(echo "${line#*=}" | tr -d '\"')" ;;
      *) ;;
    esac
  done < <(grep -E '^CONFIG_[A-Za-z0-9_]+=' "$FRAG_DIR/$f")
  while read -r line; do ./scripts/config --disable "${line#\# CONFIG }"; ./scripts/config --disable "$(echo "$line" | sed -E 's/^# CONFIG_([A-Za-z0-9_]+) is not set$/\1/')" ; done < <(grep -E '^# CONFIG_[A-Za-z0-9_]+ is not set$' "$FRAG_DIR/$f")
done
echo "  olddefconfig"
make olddefconfig >/dev/null 2>&1 || exit 1
missing=""
for s in $SYMS; do grep -qE "^CONFIG_$s=[ym\"]" .config || missing="$missing $s"; done
if [ -n "$missing" ]; then
  echo "apply.sh: FAILED, still missing:$missing"
  echo "  these are string symbols or ones whose parent is unset; check with"
  echo "  ./scripts/config --state SYMBOL and grep the Kconfig for 'depends on'"
  exit 1
fi
echo "apply.sh: all $(echo $SYMS | wc -w) recorded symbols present; .config sha256 $(sha256sum .config | cut -c1-12)"
grep -E '^CONFIG_(APPENDED_DTB_IMAGE_NAMES|APPENDED_DTBO_IMAGE_NAMES|BUILD_ARM64_APPENDED|MODULE_SIG=|SYSTEM_TRUSTED)' .config | sed 's/^/  /'
