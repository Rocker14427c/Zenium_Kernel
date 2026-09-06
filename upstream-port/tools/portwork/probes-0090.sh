#!/usr/bin/env bash
# One background session: build the OFF-state vmlinux (the "everything the rest of the kernel
# defines" set), then probe each unlanded dispsys candidate for marginal gap cost.
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

cd /home/user/portwork/series || exit 1
set +u
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
set +u
L=/home/user/portwork/logs/probes-0090.log
: > $L
echo "== [0] OFF-state vmlinux ==" | tee -a $L
make -j2 ARCH=arm64 vmlinux >> $L 2>&1
echo "OFF rc=$? vmlinux=$(ls -la vmlinux 2>/dev/null | awk '{print $5}') defined=$( ${CROSS_COMPILE}nm vmlinux 2>/dev/null | wc -l)" | tee -a $L
for f in ddp_path ddp_mmp ddp_ovl ddp_rdma_ex ddp_wdma_ex ddp_dsi ddp_disp_bdg; do
  echo "===== $f =====" | tee -a $L
  FILE=$f bash /home/user/portwork/probe-file.sh 2>&1 | tee -a $L
done
echo "=== final: dirty=$(git status --porcelain | wc -l) tree=$(git rev-parse HEAD^{tree}) ===" | tee -a $L
echo PROBES_DONE
