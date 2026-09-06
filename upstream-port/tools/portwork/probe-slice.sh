#!/usr/bin/env bash
# probe-slice.sh - price a candidate slice (list of dispsys/videox basenames) against the tree of record.
#
# Usage:  bash probe-slice.sh "ddp_ovl.c ddp_mmp.c"
#
# Prints, for that candidate set: compile diagnostics attributed to the candidate itself, the distinct
# open-name set with the switch ON, which of the currently open names it CLOSES, which names it OPENS, and
# the global-symbol collision count against the rest of the tree. Built on the three method rules established
# in the earlier rounds: whole-tree build for the ON state, name = field 2 of `nm -u` output, count DISTINCT
# names not ld reference lines. Restores the tree (tracked checkout + candidate files removed + display
# objects deleted) and prints the dirty count so the restore is verifiable.
set +u
TREE=/home/user/portwork/series
VD=/home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/dispsys
VX=/home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/videox
VC=/home/user/Zenium_Kernel/drivers/misc/mediatek/video/common
D=drivers/misc/mediatek/video/mt6768/dispsys
OPEN=${OPEN_BASE:-/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0092.txt}
CAND="${1:-}"
[ -n "$CAND" ] || { echo "usage: $0 \"file.c file2.c\""; exit 2; }
tag=$(echo "$CAND" | tr ' .' '__' | cut -c1-40)
LOG=/home/user/portwork/logs/probe-$tag.log
cd "$TREE" || exit 1
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
NM="${CROSS_COMPILE}nm"
: > "$LOG"
before=$(git status --porcelain | wc -l)
grep -E '^[A-Za-z_][A-Za-z0-9_]*$' "$OPEN" | sort -u > /tmp/open62.txt
objs=""
copied=""
for f in $CAND; do
  b="${f%.c}"; b="${b%.h}"
  src=""
  for d in "$VD" "$VX" "$VC"/*/; do
    [ -f "$d/$f" ] && { src="$d/$f"; break; }
  done
  [ -n "$src" ] || { echo "  !! $f not found in the vendor tree" | tee -a "$LOG"; continue; }
  dst="$D"
  case "$src" in *"/video/mt6768/videox/"*) dst="drivers/misc/mediatek/video/mt6768/videox";; esac
  cp "$src" "$dst/$f"
  copied="$copied $dst/$f"
  # header the platform file pairs with, if the port does not already carry it
  if [ -f "$(dirname "$src")/$b.h" ] && [ ! -f "$dst/$b.h" ]; then
    cp "$(dirname "$src")/$b.h" "$dst/$b.h"; copied="$copied $dst/$b.h"
  fi
  objs="$objs $dst/$b.o"
  echo "obj-\$(CONFIG_MTK_DISP_BRINGUP) += $b.o" >> "$dst/Makefile"
done
# the two vendor files that include <ion_sec_heap.h>, which this tree does not carry, are priced with that
# one line commented out (documented deviation; mtk_ion/ion.h on the include path gives the only type used)
for f in $copied; do
  grep -q "^#include <ion_sec_heap.h>$" "$f" 2>/dev/null &&
  sed -i 's|^#include <ion_sec_heap.h>$|/* #include <ion_sec_heap.h> */|' "$f"
done
# any file that includes "mtk_dramc.h" needs the platform dramc header + its -I dir (0085-style filtered set)
if grep -lq 'include "mtk_dramc.h"' $copied 2>/dev/null; then
  mkdir -p drivers/misc/mediatek/dramc/mt6768
  cp /home/user/Zenium_Kernel/drivers/misc/mediatek/dramc/mt6768/mtk_dramc.h drivers/misc/mediatek/dramc/mt6768/
  sed -i "s|-I\$(srctree)/drivers/misc/mediatek/cmdq/v3 |-I\$(srctree)/drivers/misc/mediatek/dramc/mt6768 -I\$(srctree)/drivers/misc/mediatek/cmdq/v3 |" "$D/Makefile"
  echo "   + mtk_dramc.h landed with a -I line for the probe" | tee -a "$LOG"
fi
./scripts/config --enable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
VXP=drivers/misc/mediatek/video/mt6768/videox
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $VXP/*.o $VXP/.*.o.cmd $VXP/built-in.a 2>/dev/null
make -j2 ARCH=arm64 -k vmlinux > "$LOG.on" 2>&1; rc=$?
{ echo "== probe: $CAND"; echo "   tree $(git rev-parse HEAD^{tree}) dirty=$before baseline $(wc -l < /tmp/open62.txt) open";
  echo "   link rc=$rc  error:$(grep -c 'error:' $LOG.on) warning:$(grep -c 'warning:' $LOG.on)";
  for f in $CAND; do b="${f%.c}";
    printf "   %-22s obj %s B   diags error:%s warning:%s\n" "$f" \
      "$(stat -c%s $D/$b.o $VXP/$b.o 2>/dev/null | head -1 || echo MISSING)" \
      "$(grep 'error:' $LOG.on | grep -cE "(\.|/)$f:[0-9]+")" "$(grep 'warning:' $LOG.on | grep -cE "(\.|/)$f:[0-9]+")";
  done; } | tee -a "$LOG"
# "fatal error:" too: a missing header is the most common way a candidate dies, and a rig that cannot
# name it reports "0 diagnostics" for a file that never reached the compiler.
grep -E "error:" "$LOG.on" | grep -oE "[a-z_0-9_./]+\.(c|h):[0-9]+:[0-9]+: (fatal )?error: .*" | sort | uniq -c | sort -rn | head -8 | sed 's/^/     /' | tee -a "$LOG"
grep "undefined reference to" "$LOG.on" | sed -E "s/.*undefined reference to \`([^']+)'/\1/" | sort -u > /tmp/names-probe.txt
n=$(wc -l < /tmp/names-probe.txt)
{ base=$(wc -l < /tmp/open62.txt); echo "   distinct open names after: $n (baseline $base)  =>  net $((n-base))"
  [ "$n" = 0 ] && echo "   (empty set = the link never ran; ignore the deltas)"
  echo "   CLOSED ($(comm -13 /tmp/names-probe.txt /tmp/open62.txt | wc -l)): $(comm -13 /tmp/names-probe.txt /tmp/open62.txt | tr '\n' ' ')"
  echo "   OPENED ($(comm -23 /tmp/names-probe.txt /tmp/open62.txt | wc -l)): $(comm -23 /tmp/names-probe.txt /tmp/open62.txt | tr '\n' ' ')"
  # nm cannot read objects from a pipe (it prints nothing); the census must take the .o files as
  # arguments. Every "globals defined by the new objects: 0" line before this fix was the rig, not the tree.
  tot=$($NM --defined-only -g $D/*.o $VXP/*.o 2>/dev/null | awk '$2!="u"{print $3}' | sort -u > /tmp/newX.txt; wc -l < /tmp/newX.txt)
  echo "   globals defined by the new objects: $tot"
} | tee -a "$LOG"

for f in $copied; do rm -f "$f"; done
git checkout -- "$D" 2>/dev/null
git checkout -- drivers/misc/mediatek/video/mt6768/videox/ 2>/dev/null
rm -rf drivers/misc/mediatek/dramc 2>/dev/null
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd $VXP/*.o $VXP/.*.o.cmd $VXP/built-in.a $VXP/.*built-in.a.cmd 2>/dev/null
./scripts/config --disable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "   restored: dirty=$(git status --porcelain | wc -l) (was $before) config=$(sha256sum .config | cut -c1-12)" | tee -a "$LOG"
echo PROBE_DONE
