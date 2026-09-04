## 1. Delta ledger (downstream 4.19.325 vs vanilla 4.19.325, mapped onto v5.15.220)

Hunks classified by `portclassify.py analyze`; every number is reproducible
from `ledger.csv`.

| metric | value |
|---|---|
| modified files in delta | 5823 |
| hunks in delta | 24622 |
| +lines / -lines of vendor delta | 288179 / 126331 |
| ALREADY in 5.15 (drop, was an upstream backport) | 9507 hunks (38%) |
| PORTABLE (pre-image matched, mechanically applied) | 2959 hunks |
| NEAR / PARTIAL (context moved, needs a human) | 4741 hunks |
| MANUAL (semantic conflict) | 4152 hunks |
| file-level: fully portable | 339 |
| file-level: obsolete (all hunks already upstream) | 1773 |
| file-level: mixed | 697 |
| file-level: manual | 1764 |
| file-level: no such file in 5.15 | 339 |
| file-level: other arch, irrelevant to this product | 911 |

Device-relevant subset (MTK/arm64-relevant paths, non-arm arches and foreign-SoC
drivers filtered out): **4429 files, 20970 hunks, 4020 manual**.

## 2. Subsystem breakdown

| subsystem | hunks | portable | already | manual+partial | applied now |
|---|---|---|---|---|---|
| `include` | 2143 | 357 | 684 | 1102 | 16% |
| `kernel` | 1943 | 334 | 671 | 938 | 17% |
| `drivers/usb/gadget` | 553 | 233 | 208 | 112 | 42% |
| `fs` | 2957 | 172 | 1401 | 1384 | 5% |
| `mm` | 900 | 169 | 221 | 510 | 18% |
| `drivers/media/platform` | 500 | 157 | 44 | 299 | 31% |
| `net` | 2360 | 144 | 1495 | 721 | 6% |
| `sound` | 462 | 119 | 187 | 156 | 25% |
| `scripts` | 577 | 90 | 337 | 150 | 15% |
| `drivers/mmc/core` | 145 | 81 | 13 | 51 | 55% |
| `drivers/gpu/drm` | 702 | 64 | 199 | 439 | 9% |
| `drivers/usb/mtu3` | 179 | 52 | 60 | 67 | 29% |
| `drivers/clk/mediatek` | 73 | 34 | 10 | 29 | 46% |
| `drivers/soc/mediatek` | 69 | 33 | 0 | 36 | 47% |
| `drivers/scsi/ufs` | 275 | 30 | 59 | 186 | 10% |
| `security` | 514 | 29 | 269 | 216 | 5% |
| `Documentation` | 280 | 24 | 39 | 217 | 8% |
| `drivers/mmc/host` | 133 | 24 | 29 | 80 | 18% |
| `lib` | 128 | 22 | 34 | 72 | 17% |
| `block` | 150 | 21 | 14 | 115 | 14% |
| `drivers/clk/clk.c` | 46 | 21 | 6 | 19 | 45% |
| `drivers/phy/mediatek` | 37 | 21 | 2 | 14 | 56% |
| `drivers/base/power` | 56 | 20 | 14 | 22 | 35% |
| `drivers/net/ethernet` | 619 | 20 | 432 | 167 | 3% |
| `drivers/usb/core` | 66 | 19 | 27 | 20 | 28% |
| `arch/arm64/boot` | 94 | 18 | 54 | 22 | 19% |

## 3. Verification of the applied subset

`portclassify.py verify` re-reads the ported tree and the pristine base.

| check | result |
|---|---|
| applied hunks whose post-image is present in the ported tree | 2952/2959 |
| hunks whose pre-image was **unique** in the base (zero misplacement risk) | 2911 |
| hunks whose pre-image matched multiple sites (nearest-to-origin chosen, flagged) | 41 |
| hunks dropped by the applier (overlapping regions) | 7 |
| files whose line delta equals the sum of their hunks exactly | 1031/1036 |

`portedcheck.py`: 29640 inserted lines scanned for APIs that changed
or vanished between 4.19 and 5.15 -> **16 hits**.

| changed/removed API | uses | files | worst file |
|---|---|---|---|
| Ion removed in 5.18 / changed before | 5 | 3 | `drivers/gpu/drm/mediatek/mtk_drm_gem.c` |
| proc_ops required since 5.6 | 5 | 1 | `drivers/phy/mediatek/phy-mtk-tphy.c` |
| strlcpy -> strscpy (6.x, deprecated 5.10+) | 3 | 2 | `kernel/locking/lockdep.c` |
| kmap -> kmap_local (5.11+) | 2 | 2 | `drivers/android/binder_alloc.c` |
| mm: mmap_sem renamed (5.8) | 1 | 1 | `mm/madvise.c` |

Header-resolution proxy: 6007 of 12723 inserted identifiers do not resolve in the target's `include/` set; 640 are `MTK_*/oplus_*` (they arrive with the vendor tree) and the rest are mostly Android/vendor-local symbols, locals and Makefile variables - this screen is deliberately conservative (see README).

## 4. Vendor-new code that cannot be hunk-ported (transplant surface)

22950 vendor-new C files / 15,959,813 lines in scope (roots: drivers/misc/mediatek, drivers/gpu, drivers/input, drivers/power, sound/soc/mediatek, drivers/net, drivers/platform, drivers/devfreq, drivers/clk, drivers/iommu, drivers/mmc, arch/arm64).

| API hazard | uses | files | why it hurts on 5.15 |
|---|---|---|---|
| `set_fs/goto_if` | 1097 | 125 | removed in 5.11; every userspace-copy path in MTK/OPLUS drivers uses it |
| `ion (removed 5.18)` | 1009 | 231 | Ion core gone; MTK's mtk_memalloc/ion glue must move to dma-buf heaps |
| `proc_fops (needs proc_ops)` | 777 | 241 | /proc drivers must convert to proc_ops (5.6) |
| `timespec (removed 5.6)` | 583 | 229 | struct timespec/y2038 rework |
| `strlcpy/strlcat` | 541 | 232 | deprecated in favour of strscpy |
| `timer_setup gap` | 254 | 151 | old timer init API must become timer_setup()/from_timer() |
| `kmap (5.11+ -> kmap_local)` | 234 | 89 | kmap_atomic semantics + HIGHMEM helpers deprecated |
| `old access_ok` | 149 | 78 | access_ok() lost the VERIFY_* argument in 5.0 |
| `get_user_pages (5.8+ -> pin_*)` | 142 | 56 | long-term pins must use pin_user_pages |
| `signal: send_sig_info sigqueue` | 27 | 12 | sigqueue allocation semantics changed |
| `dma_map_sg attrs/dma_attrs` | 19 | 12 | dma-mapping attribute API rework |
| `init_MUTEX (removed)` | 17 | 5 | long-removed mutex API |

## 5. MT6769 (phone) vs MT8365 (Genio 510) - measured

| measurement | value |
|---|---|
| compatibles instantiated by the phone's MT6765/MT6768 DTS | 404 (379 `mediatek,*`) |
| of those, bindable by a driver in **v5.15.220** | 32 (7%) |
| only the mt8365 spelling is bound in 5.15 (rename test) | 2 |
| mainline `mt8365.dtsi` compatible set | 77 |
| shared with the phone's IP | 8 |
| first release with clk-mt8365.c / mt8365.dtsi | 6.1 / 6.4 (absent from 5.15) |

Per-IP-block view for the chosen target (v5.15.220):

| IP class | device nodes | bindable in target | needs vendor/backport |
|---|---|---|---|
| other | 205 | 13 | 192 |
| modem/CCCI/connectivity | 33 | 1 | 32 |
| camera/ISP | 27 | 2 | 25 |
| display (DSI/DPI/OVL/MDP) | 24 | 0 | 24 |
| IOMMU/SMI/CMDQ/GCE | 19 | 0 | 19 |
| DVFS/thermal/cpufreq | 18 | 2 | 16 |
| power/PMIC/pwrap | 17 | 2 | 15 |
| video codec | 9 | 1 | 8 |
| memory/storage | 8 | 0 | 8 |
| USB/PHY/typec | 7 | 1 | 6 |
| clock/PLL/CGU | 7 | 4 | 3 |
| pin/pinctrl/EINT | 6 | 1 | 5 |
| security/TEE | 6 | 0 | 6 |
| serial/spi/i2c/uart | 5 | 3 | 2 |
| audio (AFE/codec) | 4 | 1 | 3 |
| input/touch/fp | 4 | 0 | 4 |
| misc/sensor | 3 | 1 | 2 |
| GPU (Mali) | 2 | 0 | 2 |

