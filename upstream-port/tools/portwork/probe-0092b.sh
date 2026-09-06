#!/usr/bin/env bash
# probe-0092b.sh - price the rdma/wdma *platform* slice (the shape 0092 actually is).
#
# Measured reason the common/ wrappers are NOT candidates: drivers/misc/mediatek/video/common/Makefile:65-78
# builds rdma20/ and wdma20/ only for CONFIG_MACH_MT6799 (and rdma10/wdma10 for an older list); mt6768 takes
# neither branch, and DDP_REG_BASE_DISP_RDMA0 - which common/rdma20/ddp_rdma.c:25 uses - is defined nowhere in
# the vendor tree except in that file's own MT6799 assumptions. So those two files are foreign-platform code
# that this board's vendor build never compiled, exactly like the v3 cmdq .c files.
#
# What is priced here: ddp_matrix_para.h (131 ln) + ddp_rdma_ex.c (1649 ln) + ddp_wdma_ex.c (1330 ln, with
# one documented deviation: its <ion_sec_heap.h> include, which the port does not carry and whose only
# contribution to this file - the ion_phys_addr_t typedef - comes from drivers/staging/android/mtk_ion/ion.h,
# already on the dispsys include path; the code that would need the header sits behind
# CONFIG_MTK_TRUSTED_MEMORY_SUBSYSTEM, which the config of record does not set).
set +u
TREE=/home/user/portwork/series
V=/home/user/Zenium_Kernel/drivers/misc/mediatek/video
LOG=/home/user/portwork/logs/probe-0092b.log
D=drivers/misc/mediatek/video/mt6768/dispsys
OPEN=/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0091.txt
cd "$TREE" || exit 1
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
NM="${CROSS_COMPILE}nm"
: > "$LOG"
before=$(git status --porcelain | wc -l)
grep -E '^[A-Za-z_][A-Za-z0-9_]*$' "$OPEN" | sort -u > /tmp/open62.txt
echo "== probe-0092b on tree $(git rev-parse HEAD^{tree}) dirty=$before, baseline $(wc -l < /tmp/open62.txt) open names ==" | tee -a "$LOG"

cp "$V/mt6768/dispsys/ddp_matrix_para.h" "$V/mt6768/dispsys/ddp_rdma_ex.c" \
   "$V/mt6768/dispsys/ddp_wdma_ex.c" "$D/"
sed -i 's|^#include <ion_sec_heap.h>$|/* #include <ion_sec_heap.h> */   /* PROBE: ion.h supplies the only type this file needs */|' \
   "$D/ddp_wdma_ex.c"
echo "  wdma_ex deviation lines: $(diff <(cat $V/mt6768/dispsys/ddp_wdma_ex.c) $D/ddp_wdma_ex.c | grep -c '^[<>]')" | tee -a "$LOG"
for f in ddp_rdma_ex ddp_wdma_ex; do echo "obj-\$(CONFIG_MTK_DISP_BRINGUP) += $f.o" >> "$D/Makefile"; done
./scripts/config --enable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a 2>/dev/null
make -j2 ARCH=arm64 -k vmlinux > "$LOG.on" 2>&1; rc=$?
echo "--- whole-tree ON link rc=$rc ---" | tee -a "$LOG"
echo "  error:=$(grep -c 'error:' $LOG.on)  warning:=$(grep -c 'warning:' $LOG.on)" | tee -a "$LOG"
grep "error:" "$LOG.on" | grep -oE "[a-z_0-9]+\.(c|h):[0-9]+" | sort | uniq -c | sort -rn | head -12 | sed 's/^/    /' | tee -a "$LOG"
for f in ddp_rdma_ex ddp_wdma_ex; do
  printf "  %-16s object %s B\n" "$f.o" "$(stat -c%s $D/$f.o 2>/dev/null || echo MISSING)" | tee -a "$LOG"
  printf "  %-16s diags: error:%s warning:%s (attributed to the .c)\n" "$f.c" \
    "$(grep 'error:' $LOG.on | grep -c " $f\.c:")" "$(grep 'warning:' $LOG.on | grep -c " $f\.c:")" | tee -a "$LOG"
done
grep "undefined reference to" "$LOG.on" | sed -E "s/.*undefined reference to \`([^']+)'/\1/" | sort -u > /tmp/names-probe.txt
n=$(wc -l < /tmp/names-probe.txt)
echo "--- distinct open names: $n (baseline 62) ---" | tee -a "$LOG"
[ "$n" = 0 ] && echo "  WARNING: empty set means the link never ran; numbers below are meaningless" | tee -a "$LOG"
echo "CLOSED by the slice ($(comm -13 /tmp/names-probe.txt /tmp/open62.txt | wc -l)):" | tee -a "$LOG"
comm -13 /tmp/names-probe.txt /tmp/open62.txt | sed 's/^/    /' | tee -a "$LOG"
echo "OPENED by the slice ($(comm -23 /tmp/names-probe.txt /tmp/open62.txt | wc -l)):" | tee -a "$LOG"
comm -23 /tmp/names-probe.txt /tmp/open62.txt | sed 's/^/    /' | tee -a "$LOG"
echo "--- per-file undefined, and whether each is already open or newly opened ---" | tee -a "$LOG"
for f in ddp_rdma_ex ddp_wdma_ex; do
  [ -f "$D/$f.o" ] || continue
  $NM -u "$D/$f.o" | awk '{print $2}' | sort -u > /tmp/u-$f.txt
  echo "    $f.o undefined: $(wc -l < /tmp/u-$f.txt) names; newly opened by it: $(comm -12 /tmp/u-$f.txt <(comm -23 /tmp/names-probe.txt /tmp/open62.txt) | wc -l)" | tee -a "$LOG"
  comm -12 /tmp/u-$f.txt <(comm -23 /tmp/names-probe.txt /tmp/open62.txt) | tr '\n' ' ' | sed 's/^/      /' | tee -a "$LOG"; echo | tee -a "$LOG"
done
echo "--- symbol census: globals these objects add, and collisions ---" | tee -a "$LOG"
$NM --defined-only -g $D/ddp_rdma_ex.o $D/ddp_wdma_ex.o 2>/dev/null | awk '$2=="T"||$2=="D"||$2=="B"||$2=="t"||$2=="b"{print $3}' | sort -u > /tmp/new92.txt
echo "  defined globals: $(grep -c . /tmp/new92.txt)" | tee -a "$LOG"
find drivers kernel lib mm fs net -name '*.o' | grep -vE "ddp_(rdma|wdma)_ex\.o" | tr '\n' '\0' | xargs -0 -n200 $NM 2>/dev/null | awk '$2=="T"||$2=="D"{print $3}' | sort -u > /tmp/treeT92.txt
echo "  collisions with the rest of the tree: $(comm -12 /tmp/new92.txt /tmp/treeT92.txt | wc -l)" | tee -a "$LOG"
comm -12 /tmp/new92.txt /tmp/treeT92.txt | head -8 | sed 's/^/    /' | tee -a "$LOG"
echo "--- of the remaining 54, what is next reachable? ---" | tee -a "$LOG"
comm -12 /tmp/names-probe.txt /tmp/open62.txt | tr '\n' ' ' | fold -w 100 | sed 's/^/    /' | tee -a "$LOG"

git checkout -- "$D/Makefile" 2>/dev/null
rm -f $D/ddp_matrix_para.h $D/ddp_rdma_ex.c $D/ddp_wdma_ex.c
git checkout -- $D/ 2>/dev/null
rm -f $D/*.o $D/.*.o.cmd $D/built-in.a $D/.*built-in.a.cmd 2>/dev/null
./scripts/config --disable MTK_DISP_BRINGUP >/dev/null 2>&1
make ARCH=arm64 olddefconfig >/dev/null 2>&1
echo "--- restored: dirty=$(git status --porcelain | wc -l) (was $before) tree=$(git rev-parse HEAD^{tree}) config=$(sha256sum .config | cut -c1-12)" | tee -a "$LOG"
echo PROBE0092B_DONE
