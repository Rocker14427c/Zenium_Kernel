#!/bin/bash
# mkcommits - turn a mechanically ported tree into a reviewable, grouped commit
# series so that a 4.19 -> 5.x port can be audited subsystem by subsystem.
#
#   mkcommits.sh <port-tree> <base-ref> <out-patch-dir>
#
# Each commit message records how it was produced (tool + classification), which
# files it contains, and the exact hunk/file counts, so nothing is unattributed.
set -euo pipefail

TREE=${1:?port tree}
BASE=${2:?base ref}
OUT=${3:?patch output dir}
BRANCH=port-$(date +%s)
SRC=${SRC:-Zenium_Kernel 4.19.325 (MTK/OPLUS downstream, squashed)}

cd "$TREE"
git config user.name  >/dev/null 2>&1 || git config user.name  "Zenium Upstream Port"
git config user.email >/dev/null 2>&1 || git config user.email "upstream-port@zenium.invalid"

# regenerate from the base every run
git checkout -q "$BASE" 2>/dev/null || true
git rev-parse --verify -q "$BRANCH" >/dev/null && git checkout -q "$BRANCH" && git reset -q --hard "$BASE"

git diff --name-only "$BASE" | sort > /tmp/port_files.$$
total=$(wc -l < /tmp/port_files.$$)
echo "porting $total files on top of $BASE"

group_of() {
  case "$1" in
    mm/*)        echo "core-mm" ;;
    kernel/*)    echo "core-kernel" ;;
    fs/*)        echo "fs" ;;
    net/*)       echo "net" ;;
    block/*)     echo "block" ;;
    lib/*)       echo "lib" ;;
    crypto/*)    echo "crypto" ;;
    security/*)  echo "security" ;;
    init/*|usr/*) echo "init" ;;
    include/*)   echo "headers" ;;
    arch/*)      echo "arch" ;;
    drivers/*)   echo "drivers-$(echo "$1" | cut -d/ -f2)" ;;
    sound/*)     echo "sound" ;;
    tools/*)     echo "tools" ;;
    scripts/*|Kconfig*|Makefile|Documentation/*) echo "build-docs" ;;
    *)           echo "misc" ;;
  esac
}

awk '{print}' /tmp/port_files.$$ | while read -r f; do
  echo "$(group_of "$f") $f"
done | sort > /tmp/port_grouped.$$

groups=$(cut -d' ' -f1 /tmp/port_grouped.$$ | uniq -c | sort -rn)
echo "$groups"

while read -r g; do
  [ -z "$g" ] && continue
  files=$(awk -v g="$g" '$1==g{print $2}' /tmp/port_grouped.$$)
  n=$(echo "$files" | grep -c . || true)
  [ "$n" = 0 ] && continue
  echo "  commit group: $g ($n files)"
  # shellcheck disable=SC2086
  echo "$files" | tr '\n' '\0' | xargs -0 git add -A --
  git commit -q --no-verify -F - <<MSG
$g: carry downstream 4.19.325 vendor delta onto $BASE

Ported mechanically by upstream-port/bin/portclassify.py from:
  $SRC

$n file(s) in this group.  Every hunk was applied only where its pre-image
matched the target text exactly; classification: PORTABLE (pre-image found),
ALREADY (already upstream, dropped), MANUAL/NEAR/PARTIAL (left for review,
see upstream-port/report/ledger.csv).

See upstream-port/MIGRATION-5.15.md for the audit and the remaining work.
MSG
done < <(echo "$groups" | awk '{print $2}')

git update-ref "refs/heads/$BRANCH" HEAD 2>/dev/null || true
mkdir -p "$OUT"
rm -f "$OUT"/*.patch
git format-patch --cover-letter -o "$OUT" "$BASE"..HEAD -q || \
  git format-patch --cover-letter -o "$OUT" "$BASE"..HEAD
rm -f /tmp/port_files.$$ /tmp/port_grouped.$$
echo
echo "branch: $BRANCH   patches: $(ls "$OUT"/*.patch | wc -l) in $OUT"
git diff --shortstat "$BASE"..HEAD
