#!/usr/bin/env bash
# Marginal-gap probe for one vendor dispsys file, measured against the landed tree of record.
# Builds the candidate object with the real config, then compares its undefined set against
# (a) what the display objects define and (b) what the OFF-state vmlinux already defines.
# Reports: does it compile, which of the 78 open names it provides, and which names it OPENS.
# Tree is restored to exactly its prior state at the end.
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

TREE=${TREE:-/home/user/portwork/series}
FILE=${FILE:-ddp_path}
LOG=${LOG:-/home/user/portwork/logs/probe-$FILE.log}
V=/home/user/Zenium_Kernel/drivers/misc/mediatek/video/mt6768/dispsys
D=drivers/misc/mediatek/video/mt6768/dispsys
OPEN=/home/user/Zenium_Kernel/upstream-port/report/l2-open-names-at-0089.txt

cd "$TREE" || exit 1
set +u
. /home/user/portwork/tools/env.sh >/dev/null 2>&1
set +u
NM="${CROSS_COMPILE}nm"
: > "$LOG"
echo "== $FILE probe on $TREE (tree $(git rev-parse HEAD^{tree})) ==" | tee -a "$LOG"
before=$(git status --porcelain | wc -l)
[ -f "$TREE/vmlinux" ] || { echo "need OFF-state vmlinux as the 'defined elsewhere' set"; exit 1; }

cp "$V/$FILE.c" "$D/$FILE.c"
echo "obj-\$(CONFIG_MTK_DISP_BRINGUP) += $FILE.o" >> "$D/Makefile"
make -j2 ARCH=arm64 CONFIG_MTK_DISP_BRINGUP=y "$D/" >> "$LOG" 2>&1
rc=$?
echo "--- compile rc=$rc; error lines attributed to $FILE.c: $(grep -cE "error:" <<<"$(grep -E "(^| )$FILE\.c" "$LOG")")" | tee -a "$LOG"
echo "--- all error lines: $(grep -c 'error:' "$LOG")   first: $(grep -m1 -E 'error:' "$LOG")" | tee -a "$LOG"
echo "--- object: $(ls -la $D/$FILE.o 2>/dev/null | awk '{print $5" bytes"}' || echo absent)" | tee -a "$LOG"

if [ -f "$D/$FILE.o" ]; then
  # what the whole gated display set defines, once the candidate is in
  find drivers/misc/mediatek -name '*.o' | sort > /tmp/dobj.txt
  echo "--- display objects in the tree: $(wc -l < /tmp/dobj.txt)" >> "$LOG"
  $NM --defined-only -g $(tr '\n' ' ' < /tmp/dobj.txt) 2>/dev/null | awk '$2=="T"||$2=="t"||$2=="D"||$2=="B"{print $3}' | sort -u > /tmp/ddef.txt
  $NM --defined-only -g "$TREE/vmlinux" 2>/dev/null | awk '{print $3}' | sort -u > /tmp/kdef.txt
  $NM -u "$D/$FILE.o" 2>/dev/null | awk '$2=="U"{print $3}' | sort -u > /tmp/cand-u.txt
  comm -23 /tmp/cand-u.txt <(cat /tmp/ddef.txt /tmp/kdef.txt | sort -u) > /tmp/cand-new.txt
  $NM --defined-only -g "$D/$FILE.o" 2>/dev/null | awk '{print $3}' | sort -u > /tmp/cand-t.txt
  echo "--- candidate defines $(wc -l < /tmp/cand-t.txt) global symbols; undefined refs $(wc -l < /tmp/cand-u.txt)" | tee -a "$LOG"
  echo "--- of the 78 open names, this file PROVIDES: $(comm -12 /tmp/cand-t.txt <(grep -E '^[A-Za-z_][A-Za-z0-9_]*$' $OPEN | sort -u) | wc -l)" | tee -a "$LOG"
  comm -12 /tmp/cand-t.txt <(grep -E '^[A-Za-z_][A-Za-z0-9_]*$' $OPEN | sort -u) | tr '\n' ' ' | tee -a "$LOG"; echo | tee -a "$LOG"
  echo "--- names it OPENS that are NOT already in the 78 (the real cost): $(wc -l < /tmp/cand-new.txt)" | tee -a "$LOG"
  grep -vxF -f <(grep -E '^[A-Za-z_][A-Za-z0-9_]*$' $OPEN | sort -u) /tmp/cand-new.txt > /tmp/cand-extra.txt
  echo "    extra beyond the 78: $(wc -l < /tmp/cand-extra.txt)" | tee -a "$LOG"
  sed 's/^/      /' /tmp/cand-extra.txt | head -30 | tee -a "$LOG"
  echo "    already-open subset: $(comm -12 /tmp/cand-new.txt <(grep -E '^[A-Za-z_][A-Za-z0-9_]*$' $OPEN | sort -u) | wc -l)" | tee -a "$LOG"
fi

# restore
git checkout -- "$D/Makefile" && rm -f "$D/$FILE.c" "$D/$FILE.o" "$D/.*$FILE.o.cmd" "$D/built-in.a" "$D/.*built-in.a.cmd"
make -j2 ARCH=arm64 "$D/" >> "$LOG" 2>&1
echo "--- cleanup: git status lines before=$before after=$(git status --porcelain | wc -l)  tree $(git rev-parse HEAD^{tree})" | tee -a "$LOG"
echo PROBE_DONE rc=$rc
