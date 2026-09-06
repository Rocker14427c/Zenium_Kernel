#!/usr/bin/env bash
# Does the full ON build actually compile videox/disp_helper.o, and how many distinct open
# names does the ON link really have? Answers whether disp_helper_get_option/_get_stage are
# genuine gaps or an artifact of the gate never descending into videox.
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
NM="${CROSS_COMPILE}nm"; L=/home/user/portwork/logs/on-full-state.log; : > $L
echo "config of record: MTK_DISP_M4U=$(grep -E '^CONFIG_MTK_DISP_M4U' .config || echo unset)  BRINGUP=$(grep -E '^CONFIG_MTK_DISP_BRINGUP' .config || echo unset)" | tee -a $L
echo "== enable MTK_DISP_BRINGUP and build vmlinux (full ON state) ==" | tee -a $L
./scripts/config --enable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >> $L 2>&1
echo "  now: BRINGUP=$(grep -E '^CONFIG_MTK_DISP_BRINGUP' .config)  M4U=$(grep -E '^CONFIG_MTK_DISP_M4U' .config)" | tee -a $L
make -j2 ARCH=arm64 -k vmlinux >> $L 2>&1; rc=$?
echo "ON rc=$rc" | tee -a $L
for d in video/mt6768/dispsys video/mt6768/videox video/common; do
  echo "  objects built under $d: $(find drivers/misc/mediatek/$d -name '*.o' 2>/dev/null | wc -l)" | tee -a $L
  find drivers/misc/mediatek/$d -name '*.o' 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ' | sed 's/^/    /' | tee -a $L; echo | tee -a $L
done
grep -c "error:" $L | sed 's/^/error lines: /' | tee -a $L
grep -E "warning:" $L | grep -cE "disp_helper\.c" | sed 's/^/disp_helper.c warnings: /' | tee -a $L
grep -E "undefined reference to" $L | grep -oE "'[^']+'" | tr -d "'" | sort -u > /tmp/on-names.txt
echo "ON distinct undefined names: $(wc -l < /tmp/on-names.txt)" | tee -a $L
for n in disp_helper_get_option disp_helper_get_stage; do
  printf "  %-26s in ON undefined set: %s   defined by disp_helper.o: %s\n" "$n" \
    "$(grep -cx "$n" /tmp/on-names.txt)" \
    "$([ -f drivers/misc/mediatek/video/mt6768/videox/disp_helper.o ] && $NM --defined-only drivers/misc/mediatek/video/mt6768/videox/disp_helper.o | grep -c " $n\$" || echo "no-obj")" | tee -a $L
done
echo "== restore the config of record ==" | tee -a $L
./scripts/config --disable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >> $L 2>&1
echo "  restored: BRINGUP=$(grep -E '^CONFIG_MTK_DISP_BRINGUP' .config || echo unset)  dirty=$(git status --porcelain | wc -l) tree=$(git rev-parse HEAD^{tree})" | tee -a $L
echo ONSTATE_DONE
