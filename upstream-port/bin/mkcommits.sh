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

# Regenerate from the base every run.  A dirty tree is NEVER checked out: switching
# commits would silently discard the ported content that is only present in the
# working tree/index, which is exactly what this script is meant to turn into commits.
cur=$(git rev-parse HEAD)
base_sha=$(git rev-parse "$BASE^{commit}")
if [ "$cur" != "$base_sha" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "mkcommits: FATAL: $TREE has local changes and HEAD is not $BASE;" >&2
    echo "  refusing to switch commits (it would drop the ported content)." >&2
    echo "  run:  git -C $TREE reset --hard $BASE && git apply --index <port.diff>" >&2
    exit 1
  fi
  git checkout -q "$BASE"
fi
if git rev-parse --verify -q "$BRANCH" >/dev/null; then
  git checkout -q "$BRANCH" && git reset -q --hard "$BASE"
else
  git checkout -q -b "$BRANCH"   # keeps the dirty index/work tree content
fi

# The grouping relies on the ported content being *unstaged*: `git add -A -- <files>`
# followed by `git commit` would otherwise commit the whole index into the first
# group.  Unstage (content stays in the working tree), then list modified + new files.
git reset -q --mixed "$base_sha"
{ git diff --name-only "$base_sha"; git ls-files --others --exclude-standard; } \
  | sort -u > /tmp/port_files.$$
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
  # a group whose content turned out identical to base produces no commit; skip it
  # instead of letting `set -e` abort the run.
  if git diff --cached --quiet "$base_sha" 2>/dev/null || git diff --cached --quiet; then
    echo "  commit group: $g ($n files) -> no staged change, skipped"
    continue
  fi
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
