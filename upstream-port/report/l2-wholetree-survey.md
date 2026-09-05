# Whole-tree survey at 0085: one real defect from 0001, and the mechanism that hid it for 84 patches

Date: 2026-09-05, same round as `l2-videox-include-regression.md`. Status: **defect measured, fix
implemented and compiling, whole-tree `-k` build in flight**; the fix is committed in the landing tree
but **not published** until that build says clean. Nothing here is claimed about hardware.

## 1. What the first whole-tree build did

`portwork/fullbuild0085.sh` (worktree at the 0085 tip, config = `make defconfig` + the two in-repo
fragments via `configs/apply.sh`, `.config` sha256 `758ae54339bf…`, `make prepare` rc=0) reached
**1,732 objects** and then:

```
drivers/acpi/fan.c:273:16: error: conflicting types for 'show_state'
  273 | static ssize_t show_state(struct device *dev, struct device_attribute *attr, char *buf)
In file included from ./include/linux/wait.h:10, ... from ./include/linux/sched.h:14, ...
./include/linux/sched/debug.h:19:20: note: previous definition of 'show_state' was here
   19 | static inline void show_state(void)
make[2]: *** [drivers/acpi/fan.o] Error 1
```

`make` stopped descending, so this single error was all that could be seen. Hence the `-k` survey.

## 2. The measurement chain (each step run, not inferred)

| question | measurement | answer |
|---|---|---|
| did the port touch either colliding file? | `git diff --name-only 0996e0926..HEAD -- drivers/acpi/ include/linux/sched/debug.h` | **empty** — both files are exactly mainline v5.15.220 |
| is it an upstream v5.15 bug then? | pristine `v5.15.220` worktree + *the same* `.config`, `make drivers/acpi/fan.o` | **rc=0, fan.o 87,160 B built** — so no, the port causes it |
| what does the port change that reaches fan.c? | `git diff 0996e0926..HEAD -- include/linux/wait.h` | **one line, from 0001**: `#include <linux/sched/debug.h>` (vendor `wait.h:10` has exactly that, measured) |
| why does that line exist at all? | `grep -c "\b__sched\b"` per file, ours vs mainline | `__sched` is defined **only** in `sched/debug.h:46`; the vendor delta *added* `__sched` annotations to 3 files that mainline leaves alone: `include/linux/pagemap.h` 0→6, `mm/filemap.c` 0→2, `kernel/sched/wait.c` 0→3. pagemap.h therefore needs `sched/debug.h` visible in **every** TU that includes it, and the vendor's way of guaranteeing that was to include it from `wait.h` |
| blast radius of the collision | `grep -rln "static ssize_t show_state(" drivers/ fs/ net/` | **exactly one file in the whole tree: `drivers/acpi/fan.c`** |
| why did no earlier gate see it? | every L1/L2 gate built named leaf dirs; `drivers/acpi` is in none of them. Vendor 4.19's own `drivers/acpi/fan.c` contains **no** `show_state` (measured: zero hits for `show_state\|DEVICE_ATTR`) — the `DEVICE_ATTR_RW(state)` naming arrived in mainline after 4.19, so the vendor hack was harmless at the source and became a collision only here |

So: a 4.19 header hack, carried faithfully, met 5.15's renamed sysfs callback in one driver. Textbook
API drift, invisible to a directory-scoped gate and to any static "does the delta apply" check.

## 3. What was ruled out, with the measurement that ruled it out

* **Just deleting the `wait.h` line** (making `wait.h` pristine) — **fails at `make prepare`**:
  `include/linux/pagemap.h:621:22: error: expected ';' before 'void'` (six more of the same, then
  `implicit declaration of 'wait_on_page_bit'`). `__sched` is not a keyword; without the include the
  annotation is a bare identifier and pagemap.h stops parsing, which poisons `kernel/bounds.s` and
  thus `prepare0`, so the tree cannot even start building. Rejected on measurement.
* **Reverting the 11 vendor `__sched` annotations instead** (pagemap.h + mm/filemap.c +
  kernel/sched/wait.c back to mainline, then deleting the `wait.h` line): compiles, but
  `__sched` = `__section(".sched.text")` decides whether `in_sched_functions()` recognises those
  addresses, i.e. it changes how a stack trace classifies frames. Undoing someone else's core-mm
  semantics to spare myself a header include is not a fix I can call behaviour-neutral, so it is not
  the chosen option; it stays on the table as an *upstream-cleanup* candidate, not as a build unblock.
* Touching `drivers/acpi/fan.c` (rename its callback): rejected — patching a mainline driver to work
  around a port-invented global include is backwards.

## 4. The fix (committed in the landing tree, unpublished pending the survey)

Two lines, both in headers the port already owns; no mainline file is touched and no vendor annotation
is undone:

```diff
--- a/include/linux/wait.h
+++ b/include/linux/wait.h
@@ -7,7 @@
 #include <linux/list.h>
 #include <linux/stddef.h>
 #include <linux/spinlock.h>
-#include <linux/sched/debug.h>
```

```diff
--- a/include/linux/pagemap.h
+++ b/include/linux/pagemap.h
 #include <linux/bitops.h>
+#include <linux/sched/debug.h>   /* for __sched, used by the carried lock_page/wait_on_page_bit
+                                  * annotations; see report/l2-wholetree-survey.md */
```

`include/linux/wait.h` returns **byte-identical to mainline** (verified with `diff` against
`v5.15.220:include/linux/wait.h` in the scratch tree), so the port's global footprint shrinks by one
core header and the `__sched` dependency is now stated in the header that has it instead of smuggled
in through the most-included file in the kernel.

Measured in the scratch tree with exactly this change: `make prepare` clean (0 error lines) and
`drivers/acpi/fan.o` builds, 87,200 B.

## 5. The `-k` whole-tree survey (in flight, and the honest reason this doc ends mid-sentence)

`portwork/fullbuild-k.sh`, in `portwork/buildfull` at "0085 tip + the 2-line fix", `-j2` with `-k` so
**every** remaining whole-tree defect is enumerated in one pass: `vmlinux` → `Image.gz-dtb` →
`modules`, each stage logged to `portwork/logs/full-k-<stage>.log` with a one-line summary (rc, seconds,
`error:` count, object count) appended to `portwork/logs/full-k.summary`, and a de-duplicated list of
distinct `error:` lines at the end. Started 16:11 from 2,684 objects (the objects built before
`wait.h`'s mtime changed are recompiled by the survey, so this is effectively a full build).

Rules for reading it when it lands:

* A green `-k vmlinux` is the first **whole-tree link** ever recorded for this series post-0081, and
  `vmlinux` size + `Image.gz-dtb` size become reportable numbers with the command that produced them.
* It is **not** a device-config claim: `make ARCH=arm64 even_defconfig` is not even available in the
  landing tree (`arch/arm64/configs/` holds only `defconfig`; measured: "Can't find default
  configuration"). The 5.15 series' config of record is defconfig + the two fragments; the flashed
  device config's shape is a separate open item, and the `apply.sh` symbol list is what makes it
  reproducible here.
* A red one is a list of the next fixes, in dependency order — which is exactly what this pass is for.
* **A records gap this exposed**: `build.json`'s full-image gates carry no `.config` hash
  (`grep -o '"[a-z_]*sha[0-9a-z_]*"' build.json` finds only `dtb_sha256_unchanged_from_build33`), and
  the pre-reset `logs/build-37.log` is gone. So build-37's "7,379 objects, 0 `error:`" cannot be
  reconciled against this fan.c failure by inspection here: it either used a config without
  `CONFIG_ACPI_FAN` or never reached that directory. Rather than argue about an unreproducible claim,
  the survey re-measures the whole tree at the current tip, and **every** future full-build gate entry
  must record its `.config` sha256 alongside the object count.
* **The stray build in the vendor tree was mine, not the environment's.** Two commit messages in this
  round were passed as `git commit -m "...backticked text..."`, and the shell executed the backticks in
  the repo root before git ever saw them: the text `` `make vmlinux` `` ran a 4.19 build in
  `/home/user/Zenium_Kernel`, created a gitignored `out/`, and substituted make's output into the commit
  message in place of the sentence it was supposed to say (both pushed messages were mangled this way, so
  they are being rewritten). The earlier version of this section blamed "some environment-side process";
  that was wrong and is corrected here. Standing rule now recorded in the report set: a commit message in
  this repo is *only* ever passed with `git commit -F -` and a **single-quoted** heredoc delimiter, for the
  same reason `git commit -am <file>` was already forbidden - the message is shell input, not just text.
  No tracked vendor file changed in either episode (`git status --porcelain` dirty=0 both times, and
  `mtk-cmdq-helper.c` / `mtk-cmdq-mailbox.c` / `cmdq_record.c` still measure 2,521 / 2,525 / 4,140), and
  `out/` was removed each time.
* The same audit caught a wrong figure of my own in three earlier docs: `cmdq_record.c` was cited as
  "4,141 lines" (in the Gate 1 cost table, the options doc twice, and the probe note). It is **4,140**
  (`wc -l` and `grep -c ''` agree; the vendor tree's tracked content is unchanged, `git status`
  dirty=0, and `mtk-cmdq-helper.c`/`mtk-cmdq-mailbox.c` still measure 2,521/2,525 as recorded). All four
  citations are corrected here rather than annotated, because the number is a measurement and there is no
  interesting history to it - I typed 4,141 once and copied it.
