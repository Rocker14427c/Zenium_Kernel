#!/usr/bin/env bash
# Precise marginal-gap measurement for the one candidate that compiles: ddp_path.c.
# nm -u prints "   U name" with no filename/type columns, so the name is field 2 (the earlier
# probe filtered on $2=="U", which matched nothing - this script is the corrected version).
#
# Method rules this probe established - do not lose them when reusing it:
#   * Measure the ON state with a WHOLE-TREE build. video/Makefile descends into videox/ on
#     obj-$(CONFIG_MTK_DISP_M4U) while the objects are gated on CONFIG_MTK_DISP_BRINGUP, so
#     `make drivers/.../dispsys/` silently drops videox and invents gaps: it made
#     disp_helper_get_option/_get_stage look undefined although videox/disp_helper.o defines both.
#   * `nm -u x.o` prints "   U name" - the name is field 2, there is no type column. Filtering on
#     $2=="U" yields an empty set, which reads as "this file opens no gaps": a false green.
#   * Count DISTINCT names, never reference lines. ld truncates per object, so the same unchanged
#     tree printed 486 and 499 reference lines while both read 78 distinct names.
set +u
TREE=/home/user/portwork/series
V=/home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/dispsys
D=drivers/misc/mediatek/video/mt6768/dispsys
OPEN=/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0089.txt
LOG=/home/user/portwork/logs/probe-path-fixed.log
cd "$TREE" || exit 1
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
NM="${CROSS_COMPILE}nm"
L=$OPEN
grep -E '^[A-Za-z_][A-Za-z0-9_]*$' "$L" | head -78 | sort -u > /tmp/open78.txt
echo "open-name list: $(wc -l < /tmp/open78.txt) names"
cp "$V/ddp_path.c" "$D/ddp_path.c"
echo 'obj-$(CONFIG_MTK_DISP_BRINGUP) += ddp_path.o' >> "$D/Makefile"
make -j2 ARCH=arm64 CONFIG_MTK_DISP_BRINGUP=y "$D/" > "$LOG" 2>&1; rc=$?
echo "compile rc=$rc  errors=$(grep -c 'error:' $LOG)  warnings=$(grep -c 'warning:' $LOG)  obj=$(stat -c%s $D/ddp_path.o 2>/dev/null)"
$NM -u "$D/ddp_path.o" 2>/dev/null | awk '$1=="U"{print $2}' | sort -u > /tmp/path-u.txt
echo "undefined refs of ddp_path.o: $(wc -l < /tmp/path-u.txt)"
find drivers/misc/mediatek -name '*.o' | sort > /tmp/dobj.txt
$NM --defined-only -g $(tr '\n' ' ' < /tmp/dobj.txt) 2>/dev/null | awk '{print $3}' | sort -u > /tmp/ddef.txt
$NM --defined-only -g "$TREE/vmlinux" 2>/dev/null | awk '{print $3}' | sort -u > /tmp/kdef.txt
comm -23 /tmp/path-u.txt /tmp/ddef.txt > /tmp/path-u2.txt          # not defined by any display object
comm -23 /tmp/path-u2.txt /tmp/kdef.txt > /tmp/path-new.txt         # nor by the rest of the kernel
echo "gaps it leaves open in the ON build: $(wc -l < /tmp/path-new.txt)  (of which already in the 78: $(comm -12 /tmp/path-new.txt /tmp/open78.txt | wc -l), NEW: $(comm -23 /tmp/path-new.txt /tmp/open78.txt | wc -l))"
echo "--- NEW names it would open:"; comm -23 /tmp/path-new.txt /tmp/open78.txt | sed 's/^/    /'
echo "--- names it provides from the 78:"
$NM --defined-only -g "$D/ddp_path.o" | awk '{print $3}' | sort -u | comm -12 - /tmp/open78.txt | tr '\n' ' '; echo
echo "--- its full undefined set (any of these stay open unless provided):"
cat /tmp/path-new.txt | tr '\n' ' '; echo
git checkout -- "$D/Makefile" && rm -f "$D/ddp_path.c" "$D/ddp_path.o" "$D/.ddp_path.o.cmd" "$D/built-in.a"
make -j2 ARCH=arm64 "$D/" >> "$LOG" 2>&1
echo "cleanup: dirty=$(git status --porcelain | wc -l) tree=$(git rev-parse HEAD^{tree})"
echo PATHPROBE_DONE
