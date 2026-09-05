#!/bin/bash
# Gate for slice 0089: MT6370 sub-PMIC DSV as the provider of the display bias rails.
# Runs in /home/user/portwork/buildfull, which is at the landing commit for this slice.
# Both directions: the board config of record (display switch OFF, PMIC ON because the board
# fragment now enables it) must link and produce an image; with the display switch ON the new
# objects must all exist, add zero new link gaps, and define every symbol exactly once.
LOG=/home/user/portwork/logs/slice0089-gate.log
: > "$LOG"; exec >>"$LOG" 2>&1
. /home/user/portwork/tools/env.sh
NM="${CROSS_COMPILE}nm"
cd /home/user/portwork/buildfull || exit 1
echo "=== gate start $(date -Is) tree=$(git rev-parse HEAD^{tree}) ==="
TREE=/home/user/portwork/buildfull /home/user/portwork/configs/apply.sh
echo "apply.sh rc=$?"
./scripts/config --disable MTK_DISP_BRINGUP
make ARCH=arm64 olddefconfig > /dev/null 2>&1
echo "config-sha-off: $(sha256sum .config | cut -c1-12)"
grep -E "^CONFIG_(MFD_MT6370_PMU|MT6370_PMU_DSV|RT_REGMAP|MFD_CORE|REGMAP_I2C)=|^# CONFIG_MTK_DISP_BRINGUP" .config | sed 's/^/  off: /'
echo "--- OFF: whole-tree vmlinux + Image.gz-dtb ---"
make ARCH=arm64 -j2 vmlinux Image.gz-dtb > /tmp/off0089.log 2>&1; rc=$?
echo "OFF rc=$rc errors=$(grep -c 'error:' /tmp/off0089.log) undef=$(grep -c 'undefined reference' /tmp/off0089.log)"
grep -E "error:|warning:" /tmp/off0089.log | grep -E "mt6370|rt-regmap|lcm_pmic" | head -8
ls -l arch/arm64/boot/Image.gz-dtb arch/arm64/boot/vmlinux 2>/dev/null | awk '{print "  "$5" "$9}'
for f in mt6370_pmu_i2c mt6370_pmu_regmap mt6370_pmu_irq mt6370_pmu_subdevs mt6370_pmu_core mt6370_pmu_dsv mt6370_pmu_dsv_debugfs; do
  o=drivers/misc/mediatek/pmic/mt6370/v1/$f.o
  [ -f "$o" ] && echo "  OFF pmic obj: $f $(( $(stat -c%s $o) ))" || echo "  OFF MISSING $f.o"
done
o=drivers/misc/mediatek/rt-regmap/rt-regmap.o; [ -f "$o" ] && echo "  OFF rt-regmap.o $(( $(stat -c%s $o) ))"
[ -f drivers/misc/mediatek/lcm/lcm_pmic.o ] && echo "  OFF ERROR: lcm_pmic.o built with the switch off" || echo "  OK: lcm_pmic.o absent with switch off"
echo "--- DTB content check (provider must be reachable) ---"
scripts/dtc/dtc -I dtb -O dts arch/arm64/boot/dts/mediatek/mt6768.dtb > /tmp/mt6768-0089.dts 2>/dev/null
echo "  dtb size: $(( $(stat -c%s arch/arm64/boot/dts/mediatek/mt6768.dtb) 2>/dev/null || echo 0 ))"
grep -nE "subpmic_pmu|mt6370_pmu_dts|mt6370_dsvp|mt6370_dsvn|mt6370,intr_gpio|dsv_pos|dsv_neg" /tmp/mt6768-0089.dts | head -12 | sed 's/^/  dts: /'
echo "--- ON: display switch ---"
./scripts/config --enable MTK_DISP_BRINGUP
make ARCH=arm64 olddefconfig > /dev/null 2>&1
make ARCH=arm64 -j2 -k vmlinux > /tmp/on0089.log 2>&1; rc=$?
echo "ON rc=$rc errors=$(grep -c 'error:' /tmp/on0089.log) undef_lines=$(grep -c 'undefined reference' /tmp/on0089.log)"
grep -E "error:|warning:" /tmp/on0089.log | grep -E "mt6370|rt-regmap|lcm_pmic" | head -8
grep -oE "undefined reference to \`[^']+'" /tmp/on0089.log | sed "s/.*\`//;s/'//" | sort -u > /tmp/names-0089.txt
echo "distinct undefined names: $(wc -l < /tmp/names-0089.txt)  (0088 baseline: $(wc -l < /tmp/names-old.txt))"
echo "  closed: $(comm -23 /tmp/names-old.txt /tmp/names-0089.txt | tr '\n' ' ')"
comm -13 /tmp/names-old.txt /tmp/names-0089.txt | sed 's/^/  NEW-GAP: /'
n=0; for f in drivers/misc/mediatek/pmic/mt6370/v1/*.o drivers/misc/mediatek/rt-regmap/rt-regmap.o drivers/misc/mediatek/lcm/*.o; do
  [ -f "$f" ] && { n=$((n+1)); echo "  obj: $(basename $f) $(( $(stat -c%s $f) ))"; }
done; echo "ON new objects: $n (expect 9)"
$NM drivers/misc/mediatek/lcm/lcm_pmic.o 2>/dev/null | grep -E " [TU] " | sed 's/^/  lcm_pmic: /'
$NM drivers/misc/mediatek/pmic/mt6370/v1/*.o drivers/misc/mediatek/lcm/*.o drivers/misc/mediatek/rt-regmap/*.o 2>/dev/null | awk '$2=="T"{print $3}' | sort -u > /tmp/newT.txt
echo "new global T symbols defined: $(wc -l < /tmp/newT.txt)"
find drivers kernel lib mm fs net -name '*.o' | grep -vE "pmic/mt6370|mediatek/lcm|rt-regmap/" > /tmp/others0089.txt
c=0; while read s; do k=$(cat /tmp/others0089.txt | xargs -n200 $NM 2>/dev/null | grep -cE " T $s\$"); [ "$k" != "0" ] && { echo "  COLLISION($k): $s"; c=$((c+1)); }; done < /tmp/newT.txt
echo "collisions with the rest of the tree: $c"
echo "--- restored config ---"
./scripts/config --disable MTK_DISP_BRINGUP; make ARCH=arm64 olddefconfig > /dev/null 2>&1
echo "final config-sha: $(sha256sum .config | cut -c1-12)"
echo "=== gate end $(date -Is) ==="
