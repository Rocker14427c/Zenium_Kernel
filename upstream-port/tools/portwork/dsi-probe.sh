#!/bin/bash
# One-off sizing probe for the DSI/component slice. For each vendor dispsys file the landed slice
# excludes: compile it in isolation against the landed include set, and report (a) whether the object
# is produced, (b) error/warning lines attributed to it, (c) how many of the landed objects' unresolved
# names it would provide. Scratch tree portwork/buildfull, restored at the end.
V=/home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/dispsys
T=/home/user/portwork/buildfull
D=drivers/misc/mediatek/video/mt6768/dispsys
cd "$T" || exit 1
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
NM="${CROSS_COMPILE}nm"

find $D $T/drivers/misc/mediatek/video/mt6768/videox -name '*.o' | sort > /tmp/landed-objs.txt
$NM -u $(cat /tmp/landed-objs.txt) 2>/dev/null | awk '$2=="U"{print $3}' | sort -u > /tmp/landed-undef.txt
echo "landed objects: $(wc -l < /tmp/landed-objs.txt)   distinct unresolved names across them: $(wc -l < /tmp/landed-undef.txt)"

printf "%-14s %6s %4s %5s %5s %8s  %s\n" FILE LINES OBJ ERR WARN PROVIDES FIRSTERROR
for f in ddp_ovl ddp_path ddp_rdma_ex ddp_wdma_ex ddp_mmp ddp_disp_bdg ddp_dsi; do
  cp $V/$f.c $D/
  [ -f $V/$f.h ] && cp $V/$f.h $D/
  echo "obj-\$(CONFIG_MTK_DISP_BRINGUP) += $f.o" >> $D/Makefile
  make ARCH=arm64 CONFIG_MTK_DISP_BRINGUP=y $D/ > /tmp/probe-$f.log 2>&1
  e=$(grep -E "error:" /tmp/probe-$f.log | grep -cE "(^| )$f\.c|in file included from $f\.c")
  etot=$(grep -c "error:" /tmp/probe-$f.log)
  w=$(grep -E "warning:" /tmp/probe-$f.log | grep -cE "(^| )$f\.c")
  obj=no; prov="-"; fe=""
  if [ -f $D/$f.o ]; then
    obj=yes
    $NM $D/$f.o | awk '$2=="T"||$2=="t"{print $3}' | sort -u > /tmp/t-$f.txt
    prov=$(comm -12 /tmp/t-$f.txt /tmp/landed-undef.txt | wc -l)
    printf "     %-12s defines %s local-T names; %s of them are in the landed undefined set\n" $f "$(wc -l < /tmp/t-$f.txt)" "$prov"
    comm -12 /tmp/t-$f.txt /tmp/landed-undef.txt | sed 's/^/        provides: /' | head -12
  else
    fe=$(grep -m1 "error:" /tmp/probe-$f.log | cut -c1-72)
  fi
  printf "%-14s %6s %4s %5s %5s %8s  %s\n" $f $(wc -l < $V/$f.c) $obj "$e/$etot" $w "$prov" "$fe"
  sed -i "/+= $f\.o$/d" $D/Makefile
  rm -f $D/$f.c $D/$f.h $D/$f.o $D/.*.$f.o.cmd
done
git checkout -q -- $D 2>/dev/null
echo "restored: tree=$(git rev-parse HEAD^{tree}) dirty=$(git status --porcelain | grep -v '^??' | wc -l)"
