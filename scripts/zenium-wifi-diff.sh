#!/usr/bin/env bash
#
# zenium-wifi-diff.sh - narrow the "Wi-Fi scans return no networks" regression.
#
# What it does (read-only, no build required):
#   1. lists the commits that touch anything that can affect Wi-Fi between two
#      refs (default: the two most recent release tags),
#   2. if both refs ship a packaged ZIP, extracts the embedded Image.gz-dtb,
#      pulls the built-in config (IKCONFIG) out of each and diffs the
#      network/wireless/firmware switches,
#   3. prints the vendor Wi-Fi driver files that differ, if any.
#
# Usage: scripts/zenium-wifi-diff.sh [good-ref] [bad-ref]
#        default: v1.6-sus-20260928  v1.7-cip137-sync-20260929
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"

GOOD="${1:-v1.6-sus-20260928}"
BAD="${2:-v1.7-cip137-sync-20260929}"
# only these trees can plausibly change scanning behaviour
PATHS=(net/wireless net/mac80211 include/net/cfg80211.h drivers/misc/mediatek/connectivity
       drivers/net/wireless arch/arm64/boot/dts arch/arm64/configs/even_defconfig)

echo "== commits between $GOOD and $BAD touching Wi-Fi-relevant paths =="
git --no-pager log --oneline --no-merges "$GOOD..$BAD" -- "${PATHS[@]}" || true
echo
echo "== diffstat of those paths =="
git --no-pager diff --stat "$GOOD" "$BAD" -- "${PATHS[@]}" || true
echo
echo "== vendor gen4m / connac driver changes (the device's real Wi-Fi stack) =="
git --no-pager diff --stat "$GOOD" "$BAD" -- drivers/misc/mediatek/connectivity 2>/dev/null || true
git --no-pager diff --stat "$GOOD" "$BAD" -- arch/arm64/boot/dts 2>/dev/null || true
echo "  (empty above = the device's built-in Wi-Fi driver and DT were NOT changed)"
echo

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
cfg_of() { # cfg_of <ref> <outfile> ; returns 1 if no packaged image with IKCONFIG
  local ref="$1" out="$2" zip
  for zip in $(git ls-tree -r --name-only "$ref" | grep -E '^(release|releases)/.*\.zip$' \
               | grep -v upgrade | sort -t/ -k1,1r); do
    git cat-file blob "$ref:$zip" > "$tmp/p.zip" 2>/dev/null || continue
    unzip -o -q -j "$tmp/p.zip" Image.gz-dtb -d "$tmp" 2>/dev/null || continue
    bash scripts/extract-ikconfig "$tmp/Image.gz-dtb" > "$out" 2>/dev/null
    if [ -s "$out" ]; then echo "  (using $ref:$zip)"; return 0; fi
  done
  return 1
}
if cfg_of "$GOOD" "$tmp/good.cfg" && cfg_of "$BAD" "$tmp/bad.cfg"; then
  echo "== built-in config diff ($GOOD -> $BAD) =="
  diff <(sort "$tmp/good.cfg") <(sort "$tmp/bad.cfg") | sed 's/^/  /'
  echo
  echo "== Wi-Fi-relevant switches, side by side =="
  for k in CONFIG_WLAN CONFIG_CFG80211 CONFIG_MAC80211 CONFIG_WLAN_DRV_BUILD_IN CONFIG_HZ \
           CONFIG_SUSPEND_SKIP_SYNC CONFIG_KSM CONFIG_MODVERSIONS CONFIG_MTK_CONN_MD; do
    printf '  %-28s %-28s %s\n' "$k" "$(grep -m1 "^$k=" "$tmp/good.cfg")" "$(grep -m1 "^$k=" "$tmp/bad.cfg")"
  done
else
  echo "(could not extract built-in configs from both refs - build a package for each to compare)"
fi
echo
echo "Verdict guide:"
echo "  * if no Wi-Fi-relevant config changed and the gen4m driver is byte-identical,"
echo "    the regression is not a kernel config/driver delta between these two refs;"
echo "    compare the flashed userspace/firmware side instead, or bisect with a"
echo "    device available (logs: dmesg | grep -iE 'wlan|conn|scan')."
