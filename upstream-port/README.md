# upstream-port - 4.19.325 (Zenium/MTK/OPLUS) -> 5.15 tooling and results

Read `MIGRATION-5.15.md` for the verdict and the numbers. This file is the recipe.

## What you get

* `patch-series/` - a 73-commit series (+ cover letter) that carries the mechanically portable part
  of the downstream delta onto **`v5.15.220`**. Apply it and you have the same tree the audit
  was run against.
* `report/` - the ledgers behind every claim (per-file classification, verification results,
  hazard census, SoC comparison).
* `bin/` - the four tools; they are generic, so re-run them against `v5.10.x`, `v6.1.x`,
  `android13-5.15` or any other base in an afternoon.

## Reproduce from scratch

```bash
# 0. reference trees (GitHub only - kernel.org/Debian/go.googlesource are blocked in some CI)
git clone --depth 1 -b v4.19.325 https://github.com/gregkh/linux.git ref-4.19.325
git clone --depth 1 -b v5.15.220 https://github.com/gregkh/linux.git ref-5.15
VENDOR=/path/to/Zenium_Kernel

# 1. the downstream delta = what the vendor changed in files vanilla 4.19.325 also has
git -c core.fileMode=false -C ref-4.19.325 --work-tree=$VENDOR diff HEAD > delta_core.patch
#    and what it added / dropped entirely
(cd $VENDOR && git ls-files -s) | awk '{print $4" "$2}' | sort > zen.lst
(cd ref-4.19.325 && git ls-files -s) | awk '{print $4" "$2}' | sort > ref.lst
comm -23 <(cut -d' ' -f1 zen.lst|sort) <(cut -d' ' -f1 ref.lst|sort) > delta_added.txt   # 29,064
comm -13 <(cut -d' ' -f1 zen.lst|sort) <(cut -d' ' -f1 ref.lst|sort) > delta_deleted.txt # 95

# 2. classify every hunk against the target base (this is the slow step: ~2 min / 5.8k files)
python3 bin/portclassify.py analyze \
    --base ref-4.19.325 --vendor $VENDOR --target ref-5.15 \
    --delta delta_core.patch --out out515 --jobs $(nproc)

# 3. apply the PORTABLE hunks to a branch of the target base
git -C ref-5.15 checkout -b port-mtk515 v5.15.220
python3 bin/portclassify.py apply --vendor $VENDOR --apply-to ref-5.15 \
    --portable out515/portable.json

# 4. verify independently (post-image presence, pre-image uniqueness, line accounting)
python3 bin/portclassify.py verify --ported ref-5.15 --portable out515/portable.json \
    --base-ref v5.15.220 --out out515/verify.json

# 5. audit the applied subset for APIs that changed/disappeared before the target
python3 bin/portedcheck.py --tree ref-5.15 --base v5.15.220 --out out515/portedcheck.json

# 6. audit the *transplant* surface (vendor-new files only) for the same class of hazard
python3 bin/apiaudit.py hazard --tree $VENDOR --only-new delta_added.txt \
    --roots drivers/misc/mediatek drivers/gpu drivers/input drivers/power \
            sound/soc/mediatek drivers/net drivers/platform drivers/devfreq \
            drivers/clk drivers/iommu drivers/mmc arch/arm64 --out out515/hazard.json

# 7. the SoC question: can an MT8365/Genio base serve an MT6769 phone?
python3 bin/soccompare.py \
    --vendor-dts $VENDOR/arch/arm64/boot/dts/mediatek/mt6765.dts \
                 $VENDOR/arch/arm64/boot/dts/mediatek/mt6768.dts \
    --target-tree ref-5.15 --target-ref v5.15.220 \
    --mt8365-dtsi /path/to/extracted/mainline/mt8365.dtsi --out out515/soccompare.json

# 8. commit series per subsystem + format-patch, then tables for the report
SRC="Zenium_Kernel 4.19.325" bash bin/mkcommits.sh ref-5.15 v5.15.220 ./patch-series
python3 bin/mkreport.py --in out515 --out out515/tables.md
```

## Semantics of the classifier (why it is safe to trust `PORTABLE`)

| state | rule |
|---|---|
| `ALREADY` | the hunk's whole **post-image** occurs in the target file -> the change is upstream already, dropped |
| `PORTABLE` | the hunk's whole **pre-image** occurs verbatim (trailing-whitespace-insensitive) in the target file -> applied in place; never fuzzed on changed lines |
| `NEAR` | pre-image matched only after trimming up to 3 *context* lines -> reported, not applied |
| `PARTIAL` | every added line exists somewhere in the target file but not as a block -> reported, not applied |
| `MANUAL` | pre-image absent -> real conflict, needs the vendor author or a human |
| `NO_TARGET` | file does not exist in the target base -> replacement decision (ion, staging, KASAN, ...) |
| `SKIP_ARCH` | file belongs to an arch this product does not ship |

Hunks are applied bottom-up per file; overlapping hunks are dropped rather than guessed
(the dropped ones are counted in `verify.json` as `POST_NOT_FOUND`).

## Known gaps / caveats

* **No compile.** A real `make` needs `flex`, `bison`, `bc` plus an AArch64 clang/gcc; if your
  CI can install them, add:
  `make -C ref-5.15 ARCH=arm64 LLVM=1 CC=clang defconfig && make -j$(nproc) Image`
  The ported set is deliberately limited to hunks whose surroundings are byte-identical in
  5.15, which is why only 16 lines in the whole series touch changed APIs - but identical
  context is not the same as type-correct.
* `portedcheck.py`'s header-resolution number is a conservative **screen**, not an error count:
  locals, Makefile variables and vendor-only symbols all show up as "unresolved".
* `report/ledger.csv` is regenerated per run; nothing in it is hand-edited.
* The 41 `AMBIGUOUS_PRE` hunks (see `report/verify.json`) are the only places where the tool
  had to choose between several matching sites; it picked the one closest to the original line
  number. Review those 41 first.

## Try the series on a fresh base

```bash
git -C ref-5.15 worktree add ../port-check v5.15.220
git -C ../port-check apply --check ../upstream-port/series/00*.patch && echo "series applies cleanly"
```
