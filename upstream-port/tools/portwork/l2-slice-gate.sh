#!/bin/bash
# l2-slice-gate.sh - re-run the L2 slice gate after a sandbox reset, or before publishing a slice.
#
# Why this is a script and not a sequence of shell one-liners: portwork/ has been wiped three times by
# sandbox resets, and each time the gate had to be re-derived from memory. That is how the 13-vs-14
# object count error happened - a hand-enumerated check loop instead of a measurement over the produced
# tree. Every number this script prints comes from the tree it just built.
#
# What it proves, and what it does NOT:
#  * proves: `git am` of the published series reproduces the recorded tree; the slice compiles from
#    scratch; every expected object exists and is non-empty; no link-visible symbol is defined twice;
#    the unresolved externals are each attributable to a specific, deliberately-not-landed provider.
#  does NOT prove (without --link): any link. This sandbox has 2 CPU / 3 GB, so the default fast pass
#    compiles only the landed directories - and a slice whose providers are not in the tree still looks
#    green there. That is exactly how 0084 sat unlinkable (507 undefined references) for a whole round,
#    so `--link` runs `make -k vmlinux` over the whole tree with CONFIG_MTK_DISP_BRINGUP off; it is a
#    cold-tree job (tens of minutes) and therefore explicit. Never infer a link from the fast pass.
#
# Usage: TREE=/home/user/portwork/series ./l2-slice-gate.sh [--expect-tree SHA] [--nm-only] [--link]
set -o pipefail
ROOT=${PORTWORK:-/home/user/portwork}
REPO=${ZENIUM_REPO:-/home/user/Zenium_Kernel}
TREE=${TREE:-$ROOT/series}
# Every directory the landed display series wires into the build. It is a LIST on purpose: the 0084
# slice left drivers/misc/mediatek/video/mt6768/videox/Makefile with `obj-y += disp_helper.o` and a
# -I set that could not resolve mmprofile.h (display_recorder.h needs drivers/misc/mediatek/mmp/), so
# `make drivers/misc/mediatek/video/` failed while every gate that named only dispsys/ stayed green.
# A per-directory gate must therefore build the PARENT of what the series wires, or it certifies the
# directories it happens to list and nothing else.
DISP=drivers/misc/mediatek/video/mt6768/dispsys
SLICE_DIRS="drivers/misc/mediatek/video/mt6768/dispsys drivers/misc/mediatek/video/mt6768/videox"
VIDEO=drivers/misc/mediatek/video
# The sibling dirs the landed display glue depends on. Building them in the same pass is what makes a
# regression in 0078-0083 (SMI/M4U/CMDQ) visible here instead of at the next slice.
DEPS="drivers/mailbox/ drivers/soc/mediatek/ drivers/misc/mediatek/smi/ drivers/misc/mediatek/m4u/"
EXPECT_TREE=""
NMONLY=""
LINK=""
while [ $# -gt 0 ]; do
  case "$1" in
    --expect-tree) EXPECT_TREE=$2; shift 2 ;;
    --nm-only) NMONLY=1; shift ;;
    --link) LINK=1; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done
. "$ROOT/tools/env.sh" || exit 1
NM=${CROSS_COMPILE}nm
[ -x "$(command -v "$NM")" ] || NM=nm          # host nm reads foreign ELF only if binutils is multi-target
cd "$TREE" || exit 1
fail=0
say(){ printf '%s %s\n' "$(date -u +%H:%M:%S)" "$*"; }
ok(){ echo "  PASS $*"; }
bad(){ echo "  FAIL $*"; fail=$((fail+1)); }

say "== [1/5] tree identity =="
T=$(git rev-parse HEAD^{tree})
D=$(git status --porcelain | grep -cv '^??' || true)          # tracked modifications only
U=$(git status --porcelain | grep -c '^??' || true)           # generated files this build left behind
say "  tree=$T  commits=$(git rev-list --count HEAD)  dirty=$D tracked (+$U untracked build outputs)  describe=$(git describe --tags)"
# Tracked state is what "the built tree IS the published tree" means. Untracked entries are expected in a
# tree you just built (the 0069 packaging rule leaves arch/arm64/boot/Image.gz-dtb, which the kernel
# .gitignore does not name), so they are reported and not failed on. A forgotten NEW source file is caught
# where it belongs: the tree-hash compare against the published .eml set below.
[ "$U" -gt 0 ] && say "  untracked: $(git status --porcelain | grep '^??' | sed 's/^?? //' | head -3 | tr '\n' ' ')$([ "$U" -gt 3 ] && echo "... ($U total)")"
[ "$D" = 0 ] && ok "worktree has no tracked modifications (the built tree is the published tree)" || bad "dirty=$D"
if [ -n "$EXPECT_TREE" ]; then
  [ "$T" = "$EXPECT_TREE" ] && ok "tree == expected $EXPECT_TREE" || bad "tree $T != expected $EXPECT_TREE"
fi

say "== [2/5] full compile pass (object dir cleared first, so nothing is inherited) =="
if [ -z "$NMONLY" ]; then
  for d in $SLICE_DIRS; do rm -f $d/*.o; done
  LOG=$ROOT/logs/l2-slice-build.log
  # CONFIG_MTK_DISP_BRINGUP=y is passed on the command line, not written into .config: the objects
  # 0084/0085 landed are gated off by default (that is what makes the tree link), so a slice gate has
  # to ask for them; leaving .config untouched keeps "the published config state" a separately
  # checkable fact and keeps this pass non-destructive. kbuild expands obj-$(CONFIG_...) from make
  # variables, so this works without olddefconfig.
  make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" -k CONFIG_MTK_DISP_BRINGUP=y $VIDEO/ $DEPS > "$LOG" 2>&1
  RC=$?
  ERR=$(grep -c "error:" "$LOG")
  WARN=$(grep -c "warning:" "$LOG")
  say "  make rc=$RC  error: lines=$ERR  warning: lines=$WARN  (log: $LOG)"
  # rc=0 is required; -k is only there so one failure does not hide the next missing header.
  [ "$RC" = 0 ] && ok "build returned 0" || bad "build rc=$RC"
  [ "$ERR" = 0 ] && ok "no error: lines" || bad "$ERR error: lines (see $LOG)"
else
  say "  --nm-only: skipping the build, checking the objects that are already there"
fi

say "== [3/5] every expected object exists and is non-empty =="
# The list comes from the Makefile in the tree, NOT from a list typed into this script: obj-y in
# $DISP/Makefile is the definition of what the slice is, and hand-copying it is exactly the mistake
# that reported 13 for a 14-object slice.
# s|...|...| because the replacement is a path full of slashes - with s/.../.../ this silently
# became "unknown option to `s'" and the gate then cheerfully reported 1 object.
# `obj-[^+]*+= <name>.o` covers both shapes kbuild uses here: the bare `obj-y +=` a probe writes and the
# gated `obj-$(CONFIG_MTK_DISP_BRINGUP) +=` 0087 introduced. An earlier revision of this line matched
# only `obj-y`, which after 0087 silently collapsed the expected list to 1 entry and the existence check
# then passed trivially - a count that no longer described the slice. See the RAW cross-check below.
WANT=$(for d in $SLICE_DIRS; do [ -f "$d/Makefile" ] || continue
         sed -n "s|.*obj-[^+]*+= \([a-z_0-9]*\.o\).*|$d/\1|p" "$d/Makefile"; done | sort -u)
RAW=$(for d in $SLICE_DIRS; do [ -f "$d/Makefile" ] || continue
        grep -cE "^[[:space:]]*obj-[^+]*\+= *[a-z_0-9]+\.o" "$d/Makefile"; done | paste -sd+ | bc)
NW=$(echo "$WANT" | wc -l)
missing=""; empty=""
for o in $WANT; do
  [ -f "$o" ] || { missing="$missing $(basename $o)"; continue; }
  s=$(stat -c%s "$o"); [ "$s" -gt 0 ] || empty="$empty $(basename $o)"
done
say "  $NW objects listed by the obj- lines of: $SLICE_DIRS"
  check "$NW" = "$RAW" "the expected-object list covers every obj line in those Makefiles ($RAW found independently; a mismatch means this script's pattern has drifted from kbuild's syntax, not that the build is wrong)"
for o in $WANT; do
  [ -f "$o" ] && printf '     %-24s %8d B\n' "$(basename $o)" "$(stat -c%s "$o")" \
              || printf '     %-24s MISSING\n' "$(basename $o)"
done
[ -z "$missing" ] && ok "all $NW objects present" || bad "absent:$missing"
[ -z "$empty" ] && ok "all $NW objects non-empty" || bad "empty:$empty"
# A generated Makefile can also forget to list an object that the slice intends to build; cross-check
# against the .c files actually in the directory so an omission cannot hide as a pass.
NOTBUILT=$(for d in $SLICE_DIRS; do (cd $d && for c in *.c; do b=${c%.c}.o
     echo "$WANT" | grep -qx "$d/$b" || echo "$d/$c"; done); done 2>/dev/null | tr '\n' ' ')
say "  .c files present but not in obj-y: ${NOTBUILT:-none}"

if [ "$NW" = 0 ]; then say "no objects to analyse, stopping"; exit 1; fi
OBJS=$(for d in $SLICE_DIRS; do ls $d/*.o 2>/dev/null; done)

say "== [4/5] duplicate link-visible definitions across the slice =="
# Only T/D/B/R are link-visible; 't'/'d'/'b' are file-local clones and a second `static` copy of a
# helper is not a violation. Counting lowercase letters was an earlier false alarm here.
DUPFILE=$(mktemp)
for f in $OBJS; do $NM --defined-only "$f" 2>/dev/null | awk -v F="$f" '$2 ~ /^[TDBR]$/ {print $3, F}'; done > "$DUPFILE"
DUP=$(awk '{print $1}' "$DUPFILE" | sort | uniq -d)
NDEF=$(wc -l < "$DUPFILE")
if [ -z "$DUP" ]; then ok "$NDEF link-visible symbols defined, 0 of them twice"; else
  bad "multiply defined: $(echo "$DUP" | tr '\n' ' ')"
  for s in $DUP; do grep "^$s " "$DUPFILE" | sed 's/^/     /'; done
fi

say "== [5/5] unresolved externals: classify, and do not call it a link =="
# bin/undeps.py does the classification: "satisfied" (some .o here defines it), "core (vmlinux)"
# (declared in a mainline header - the provider is the rest of the kernel, which a per-directory pass
# does not build), "provider landed, not built here" (a .c in this tree, object absent), and
# "PROVIDER NOT LANDED" (nothing in this tree defines it; attributed to the vendor file that does).
# A plain `nm -u` diff against this partial tree is NOT that list: it also reports every kernel core
# symbol as missing, which is how an earlier round wrongly reported snprintf as a blocker.
UND=$REPO/upstream-port/bin/undeps.py
[ -f "$UND" ] || UND=$ROOT/undeps.py
CROSS_COMPILE="$CROSS_COMPILE" python3 "$UND" --tree "$TREE" --objs $SLICE_DIRS --vendor "$REPO" 2>&1 | sed 's/^/  /'
NOTLANDED=$(CROSS_COMPILE="$CROSS_COMPILE" python3 "$UND" --tree "$TREE" --objs $SLICE_DIRS --vendor "$REPO" \
  --json 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print(sum(1 for x in d if x["class"] in ("PROVIDER NOT LANDED","unattributed")))')
say "  $NOTLANDED name(s) have no provider in this tree; that set defines the next slice, not a link"
if [ "$LINK" = "1" ]; then
  say "== [L] link step: the whole tree must LINK with the bring-up gate off (the default a user builds) =="
  # Stale built-in.a files are the trap here: a directory's archive is not rebuilt just because its
  # children's objects were deleted by hand, so a link run that reuses a gate-on object state reports
  # the old undefined references and looks like a failure of the patch under test. Both were measured
  # the hard way in the 0087 round. Cleaning the video subtree's generated state is therefore part of
  # the step, because the fast pass above deliberately builds the slice WITH the switch on - the link
  # pass must not inherit those objects, or it reports this slice's known provider gap as a new failure.
  find "$TREE"/drivers/misc/mediatek/video \( -name '*.o' -o -name 'built-in.a' -o -name '.*.cmd' \) -delete 2>/dev/null
  LOG=$ROOT/logs/l2-slice-link.log
  make -j"$(nproc)" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" -k vmlinux > "$LOG" 2>&1; lrc=$?
  errs=$(grep -c " error:" "$LOG"); refs=$(grep -c "undefined reference" "$LOG")
  say "  make vmlinux rc=$lrc  error: lines=$errs  undefined-reference lines=$refs  (log: $LOG)"
  check "$lrc" = "0" "vmlinux linked"
  check "$errs" = "0" "no error: lines in the link pass"
  check "$refs" = "0" "no undefined references (a non-zero count here means the slice is not self-linking;
        for the display dirs that is expected *only* with CONFIG_MTK_DISP_BRINGUP=y - the gate must be off)"
  if [ -f "$TREE/vmlinux" ]; then
    say "  vmlinux $(stat -c%s "$TREE/vmlinux") B  sha256 $(sha256sum "$TREE/vmlinux" | cut -c1-12)..."
    say "  display symbols in vmlinux (expect 0 with the gate off): $(${CROSS_COMPILE}nm "$TREE/vmlinux" | grep -cE ' T (disp_helper_|ddp_|display_recorder)')"
    say "  NOTE: the sha256 of vmlinux/Image is not stable across commits - the version string embeds"
    say "        'git describe' (UTS_RELEASE/-g<sha>), so identical code from a different commit differs"
    say "        in those bytes. Compare sizes and the appended-DTB payload, not hashes, between rounds."
  fi
fi

say "== verdict =="
if [ "$fail" = 0 ]; then say "  GATE GREEN ($NW objects, 0 dup, unresolved externals attributed above)"; else say "  GATE FAILED: $fail check(s) failed"; fi
exit $fail
