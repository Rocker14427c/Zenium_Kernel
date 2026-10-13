# Zenium Kernel RUI4 — V1.8 (timer tick 250 Hz)

Branch `arena/01a0eb93-zenium-kernel`, built on top of **`25717d95ae75`**
(BakaSU + NoMount v2.1.0 + SUSFS v2.3.0).

**The DVFS change from the previous V1.8 has been removed.** The branch head
was moved back to `25717d95`, the `smoothcpu-v1.8` tag and release were
deleted, and the little-cluster OPP table is byte-for-byte MediaTek's stock
ladder again (verified in the built image). **This build changes exactly one
kernel symbol: `CONFIG_HZ` 300 → 250.**

* **Kernel:** `4.19.325-cip136-st20-Zenium`
* **Root manager:** BakaSU `v4.2.0-rc3-5b76b884@BakaSU` (version code 35222)
* **SUSFS:** **v2.3.0 — untouched**
* **NoMount:** **v2.1.0 — untouched**
* **Build:** rc=0, **0 errors**, 0 warnings from cpufreq / SUSFS / NoMount / BakaSU
* **AnyKernel3**, patches `boot` only, `IS_SLOT_DEVICE=0`

Devices: RMX3430, RMX3191, RMX3193, RMX3195, RMX3197, `even`.

---

## 1. The change

```
-# CONFIG_HZ_250 is not set
-CONFIG_HZ_300=y
+CONFIG_HZ_250=y
+# CONFIG_HZ_300 is not set
 # CONFIG_HZ_1000 is not set
-CONFIG_HZ=300
+CONFIG_HZ=250
```

`arch/arm64/configs/even_defconfig`, 3 lines. Nothing else.

`CONFIG_HZ` is the rate of the periodic scheduler tick. 250 Hz means **~17%
fewer timer interrupts per second** than 300 Hz. Every tick runs scheduler
accounting, timer-wheel processing and load-balancing work, so fewer ticks is
directly less work — and less work is less power.

Note that `CONFIG_HZ` is a *derived* symbol; the real switch is the
`HZ_250` / `HZ_300` choice from `kernel/Kconfig.hz`. (The first attempt at
this only edited `CONFIG_HZ=`, which Kconfig silently regenerated — the build
log confirms `CONFIG_HZ 250` is what actually got compiled in.)

---

## 2. Why this one, and why it's safe

### 2.1 Why this is the only lever that exists

I audited every power-relevant setting in this kernel before changing
anything:

| area | state |
|---|---|
| cpufreq governor | `SCHEDUTIL` — already the best governor for battery |
| cpuidle governor | `MTK_MENU` — MediaTek's own governor, tuned for this SoC |
| `NO_HZ_IDLE` | on — the tick is already suppressed while idle |
| `HIGH_RES_TIMERS` | on — timers are hrtimer-driven, not tick-driven |
| KASAN / UBSAN / LOCKDEP / kmemleak / DEBUG_INFO | **all off** — already a clean production build |
| MTK scheduler monitors, perf trackers, FPSGO | **not enabled** — no extra scheduling overhead |
| DEVFREQ governors | all off — GPU DVFS is SSPM-driven, not Linux |

There is no debug instrumentation left to strip and no wasteful vendor
feature left to disable.

I also diffed the whole power-relevant config against
**`s47user/android_kernel_samsung_a06`** — an "optimized custom 4.19.191
kernel" for the Samsung Galaxy A06, which is the *same* MT6768 / Helio G85
SoC. Across 35 power-relevant symbols, **`CONFIG_HZ` was the only meaningful
difference** (250 there, 300 here).

### 2.2 Why 250 is safe here

* **It is mainline's own default for arm64.** `kernel/Kconfig.hz` says
  `default HZ_250`. The 300 Hz setting in this tree is a vendor override, not
  an upstream default.
* **It is already proven on this exact silicon** by another vendor's BSP for
  the same SoC (Samsung A06 / MT6768).
* **No vendor code hardcodes a tick rate.** I grepped the MTK power stack,
  `drivers/cpufreq/` and `kernel/sched/` for tick-rate arithmetic. The only
  hits are `N * HZ` second-based timeouts (`ACCDET_INIT_WAIT_TIMER`,
  `ADSP_READY_TIMEOUT`, …) and `msecs_to_jiffies()` calls — both scale
  automatically with `CONFIG_HZ` and stay correct at 250.
* **The MTK cpufreq driver has no jiffies-based timing at all** — it only
  `#include`s `<linux/jiffies.h>` without using it.
* **Android userspace adapts.** `sysconf(_SC_CLK_TCK)` reads the value the
  kernel advertises; nothing in Android assumes 300.
* **`SCHED_HRTICK` is `def_bool HIGH_RES_TIMERS`** — it stays on regardless,
  so scheduling latency behaviour is unchanged.

### 2.3 The one honest trade-off

MediaTek's Kconfig help text for `HZ_300` says to pick it *"if you are going
to be using NTSC video or multimedia"* — 300 divides evenly by both 25 and
30 fps, 250 does not. That is presumably why this BSP selected 300.

In practice video playback on Android is driven by hrtimers and the display
vsync, not by the scheduler tick, and `HIGH_RES_TIMERS` is on — so the
theoretical concern should not manifest. **But I cannot test video playback
on your phone, so if you notice any stutter, this is the first thing to
suspect** and `bakasu-nomount-2.1` is one flash away.

---

## 3. Verification

| check | result |
|---|---|
| build exit code | **0** |
| compile errors | **0** |
| warnings from cpufreq / SUSFS / NoMount / BakaSU | **0** (all 78 warnings are pre-existing vendor/Oplus/MTK) |
| `CONFIG_HZ` compiled into the kernel | **250** (`out/include/generated/autoconf.h`) |
| `HZ_250` selected / `HZ_300` unset in final `.config` | **yes** |
| little-cluster DVFS ladder in image | **stock** (MediaTek's 500/774/850/…/1700 ladder present) |
| previous "smooth" DVFS ladder in image | **absent** |
| big-cluster DVFS ladder in image | **stock, unchanged** |
| `BakaSU version code` | **35222** (submodule 4522 commits — not the 30701 shallow-clone bug) |
| `susfs_inline` hook checks | **14/14 pass** |
| `SUSFS_VERSION` | **v2.3.0** |
| NoMount | **v2.1.0**, `nomount_init` = 1 |
| `susfs_*` / `nomount_*` / `nm_*` / `ksu_*` symbols | 65 / 13 / 41 / 226 |
| the 10 SUSFS hooks in `System.map` | each exactly **once** |
| `TAGLMK` / `ReSukiSU` strings in image | **0 / 0** |
| `CONFIG_NOMOUNT` / `CONFIG_KSU_SUSFS` / `CONFIG_KSU` | `y` / `y` / `y` |
| all 9 `CONFIG_KSU_SUSFS_*` sub-features | `y` |
| embedded `Image.gz-dtb` | 18,073,599 B, byte-identical to build output |

The release zip was rebuilt from the previous AK3 template with the new
`Image.gz-dtb` and a bumped `kernel.string`.

---

## 4. What to realistically expect

Honestly: **a small improvement, not a dramatic one.** 250 Hz removes about
17% of the scheduler ticks that happen while the CPU is awake; since
`NO_HZ_IDLE` already stops the tick during idle, the saving applies mainly to
active use. Expect a few percent of standby/screen-on time, not a
transformation.

The bigger battery factors on a Narzo 50A are outside the kernel — screen
brightness, radio, and which apps run in the background.

## 5. Flash instructions

1. Copy `Zenium-Kernel-RUI4-V1.8-susfs-4-bakasu-nomount-2.1-hz250.zip` to the phone.
2. Flash from recovery, or from the BakaSU manager.
3. Reboot. Patches `boot` only, `IS_SLOT_DEVICE=0`, no wipe needed.

**To go back:** `bakasu-nomount-2.1` (commit `25717d95ae75`) is the identical
build with `CONFIG_HZ=300`, still published.

**Not tested on hardware** — I cannot flash your phone. This build differs
from the one you are already running by one config symbol.
