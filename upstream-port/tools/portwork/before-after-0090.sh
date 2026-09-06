#!/usr/bin/env bash
# Definitive before/after for the ddp_path.c slice, measured with the real ON build (the whole
# gated set, not one directory) and ld's actual message format:
#   ld: drivers/.../foo.o:NNN: undefined reference to `name'
# ld truncates per object, so count DISTINCT NAMES, never reference lines.
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
cd /home/user/portwork/series || exit 1
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
LOGS=/home/user/portwork/logs
D=drivers/misc/mediatek/video/mt6768/dispsys
OPEN=/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0089.txt
grep -E '^[A-Za-z_][A-Za-z0-9_]*$' "$OPEN" | head -78 | sort -u > /tmp/open78.txt

parse() { grep "undefined reference to" "$1" | sed -E "s/.*undefined reference to \`([^\']+)'/\1/" | sort -u; }
count() { echo "  errors=$(grep -c 'error:' $1)  warnings=$(grep -c 'warning:' $1)  undefined_lines=$(grep -c 'undefined reference to' $1)  distinct_names=$(parse $1 | wc -l)"; }

echo "== BEFORE: ON build as landed (config already restored, re-enable for the link) =="
./scripts/config --enable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
make -j2 ARCH=arm64 -k vmlinux > $LOGS/on-before.log 2>&1; echo "  link rc=$?"
count $LOGS/on-before.log
parse $LOGS/on-before.log > /tmp/names-before.txt
comm -13 /tmp/names-before.txt /tmp/open78.txt | sed 's/^/  in 78 not in this run: /' | head -6
comm -23 /tmp/names-before.txt /tmp/open78.txt | sed 's/^/  in this run not in the 78: /' | head -6

echo "== AFTER: same build with ddp_path.c added (stock file, one Makefile line) =="
cp /home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/dispsys/ddp_path.c $D/
echo 'obj-$(CONFIG_MTK_DISP_BRINGUP) += ddp_path.o' >> $D/Makefile
make -j2 ARCH=arm64 -k vmlinux > $LOGS/on-after.log 2>&1; echo "  link rc=$?"
count $LOGS/on-after.log
echo "  warnings attributed to ddp_path.c: $(grep 'warning:' $LOGS/on-after.log | grep -c ' ddp_path\.c:')"
echo "  errors attributed to ddp_path.c:   $(grep 'error:' $LOGS/on-after.log | grep -c ' ddp_path\.c:')"
echo "  object: $(stat -c%s $D/ddp_path.o 2>/dev/null) bytes   display objects now: $(find drivers/misc/mediatek -name '*.o' | wc -l)"
parse $LOGS/on-after.log > /tmp/names-after.txt
comm -13 /tmp/names-after.txt /tmp/names-before.txt | sed 's/^/  CLOSED by the slice: /'
comm -23 /tmp/names-after.txt /tmp/names-before.txt | sed 's/^/  OPENED by the slice: /'
echo "  distinct names: before $(wc -l < /tmp/names-before.txt) -> after $(wc -l < /tmp/names-after.txt)"

echo "== restore =="
git checkout -- $D/Makefile && rm -f $D/ddp_path.c $D/ddp_path.o $D/.*ddp_path.o.cmd
./scripts/config --disable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "  dirty=$(git status --porcelain | wc -l) tree=$(git rev-parse HEAD^{tree}) BRINGUP=$(grep -cE '^CONFIG_MTK_DISP_BRINGUP=y' .config)"
echo BEFOREAFTER_DONE
