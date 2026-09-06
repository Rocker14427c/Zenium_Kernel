# Narrow B′, designed against measurements: what the record layer actually needs

Date: 2026-09-05, after the published-series gate came back clean (0087, tree `deba5bd29ec656ecb9b542837198cccc76cc5a09`)
and the repository was synchronised (`d7a54c4ab` pushed, local == remote). This is **design only**: no code was
written, no slice landed, nothing was flashed. It exists because the landing decision (144) chose narrow B′ -
land the vendor chunk/packet-buffer record model only as deep as the landed core needs - and the survey said the
next step is to work out what that costs before writing it.

Everything below was measured in `portwork/buildpub` (the tree produced by `git am` of the 87 published `.eml`
files) and in the vendor 4.19.325 tree at the repository root. Line and bit numbers are from those files.

## 1. The need, exactly as the landed tree states it

Four symbols, no more. `undeps.py` counted 87 names with no provider at 0085; these four are the record layer's
share, and every one of them is reached from a file that is in the landed 15 objects. Measured after 0088 landed,
"reached" is not one number: `cmdqBackup{Allocate,Read,Write}Slot` are reached from `ddp_drv.c`/`ddp_manager.c`
source text (3 callsites, 3 link references), while `cmdqRecWrite` is reached **29 times at link time from 2
objects** (`ddp_mutex.o`, `ddp_rsz.o`) through the `ddp_reg.h` macros - an earlier note here said "2 refs", which
counted the referencing *objects* and not the references, and under-sold the size of the gap by an order of
magnitude:

| symbol | callsite(s) in landed code | shape the caller expects |
|---|---|---|
| `cmdqRecWrite` | `dispsys/ddp_reg.h:205, 216, 232` (the `DISP_REG_MASK` / `DISP_REG_SET` / `DISP_REG_SET_FIELD` macros, used by `ddp_mutex.o`, `ddp_rsz.o` and everything else that includes `ddp_reg.h`) | `cmdqRecWrite(handle, disp_addr_convert(reg32), value, mask)` - 4 args, the 4th is a **mask**, and the 2nd is an **absolute APB address**, not a subsys/offset pair |
| `cmdqBackupAllocateSlot` | `ddp_drv.c:95` inside `_disp_init_cmdq_slots(pSlot, count, init_val)` | `(cmdqBackupSlotHandle *pSlot, int count)` |
| `cmdqBackupWriteSlot` | `ddp_drv.c:98` | `(handle, index, value)` |
| `cmdqBackupReadSlot` | `ddp_drv.c:108` inside `_disp_get_cmdq_slots()` | `(handle, index, u32 *value)` → `int`, non-zero is an error the caller logs |

The `handle == NULL` branch in all three macros is the CPU path (`mt_reg_sync_writel`), and the earlier
conclusion stands: replacing the CMDQ branch with the CPU branch would change vblank-time behaviour, so it is
fabrication, not a port. That is why the record layer cannot be skipped.

## 2. What `cmdqRecWrite` is, in the vendor engine (this is the part that changed my assumption)

`cmdq_record.h:167` declares `s32 cmdqRecWrite(struct cmdqRecStruct *handle, u32 addr, u32 value, u32 mask)` -
the 4-arg form the dispsys macros use. Its implementation chain is:

    cmdqRecWrite → cmdq_op_write_reg (v3/cmdq_record.c:1368) → cmdq_append_command → cmdq_append_rw_s_command (:847)

and `cmdq_op_write_reg` does **not** emit the plain `CMDQ_CODE_WRITE` that mainline models. Measured at
`cmdq_record.c:1374-1393`: with `mask != 0xFFFFFFFF` it first emits `CMDQ_CODE_MOVE` carrying `~mask`, and then
the write itself is `CMDQ_CODE_WRITE_S_W_MASK`, else `CMDQ_CODE_WRITE_S` - the *32-bit-address* opcodes - with
the address passed straight through as `arg_a`.

So the engine the landed macros expect is the WRITE_S family. Two consequences: the 12 enum values our ported
header lacks are irrelevant except for `WRITE_S*` (which mainline already has) and `MOVE` (which mainline
expresses as `LOGIC`/`ASSIGN`), and nothing in the landed path needs the vendor chunk/packet-buffer machinery
that made option A unimplementable.

## 3. The encodings are the same word. Measured, not assumed.

Vendor packing (`cmdq_record.c:957` + `:936-947`, mask from `cmdq_def.h:87`):

    new_arg_a = (addr & 0xffff) | ((subsys & 0x1f) << subsys_bit)   /* subsys_bit = getSubsysLSBArgA() = 16 */
                | (arg_type << 21)                                  /* arg_type = (addr_t << 2) | (value_t << 1) */
    *va       = (u64)((code << 24) | new_arg_a) << 32 | arg_b        /* cmdq_append_command_pkt, :913 */

Mainline 5.15.220 `struct cmdq_instruction` (`drivers/soc/mediatek/mtk-cmdq-helper.c`, the struct is private to
that file - the only copy in the tree):

    union { u32 value; u32 mask; struct { u16 arg_c; u16 src_reg; }; }   /* bits 32-63 */
    union { u16 offset; u16 event; u16 reg_dst; }                        /* bits 16-31 */
    union { u8 subsys; struct { u8 sop:5; u8 arg_c_t:1; u8 src_t:1; u8 dst_t:1; }; }  /* bits 8-15 of hi */
    u8 op;                                                              /* bits 0-7 of hi */

`cmdq_pkt_write_s_mask_value(pkt, u8 high_addr_reg_idx, u16 addr_low, u32 value, u32 mask)` emits
`CMDQ_CODE_MASK` with `mask = ~mask` (`mtk-cmdq-helper.c:285+`), then `CMDQ_CODE_WRITE_S_MASK` with
`sop = high_addr_reg_idx`, `offset = addr_low`, `value` inline.

Field-by-field, `sop:5` occupies the 5 bits at 16-20 of `arg_a` - exactly `CMDQ_ARG_A_SUBSYS_MASK 0x001F0000` -
and the mainline `MASK` opcode does what the vendor's `MOVE`+mask pair does. So for a table-resolvable address:

    cmdqRecWrite(handle, pa, value, mask)  ≡  cmdq_pkt_write_s_mask_value(pkt, subsys_id, pa & 0xffff, value, mask)
    cmdqRecWrite(handle, pa, value, ~0)    ≡  cmdq_pkt_write_s_value(pkt, subsys_id, pa & 0xffff, value)

one instruction each, no extra GPR, no chunk list. This is the result that makes narrow B′ cheap, and it was not
known when the option list was written.

**Measured at 0091, so the paragraph above no longer carries the claim alone.**
`upstream-port/tests/mtk_disp_record_host_check.c` encodes the addresses this tree can actually pass
(mmsys_config, disp_dither, and three that no row covers) under every mask `DISP_REG_SET` can spell, on both
sides, and compares the 64-bit words: 55 cases, 0 mismatches. Two header facts came out of the same run and
they are what makes the equivalence mechanical rather than arguable - the port's `CMDQ_CODE_MASK` and the
vendor's `CMDQ_CODE_MOVE` are both 0x02, and the port's `CMDQ_CODE_WRITE_S_MASK` and the vendor's
`CMDQ_CODE_WRITE_S_W_MASK` are both 0x91, so the two-instruction masked write is the same two instructions by
number as well as by layout. The harness reads those numbers out of both trees'
`include/linux/mailbox/mtk-cmdq-mailbox.h` at run time instead of restating them, and the gate log pins the
one transcription in it (the private `struct cmdq_instruction` and the two write_s helpers of
`mtk-cmdq-helper.c`) by sha256: `37d6ddcf5659`, `fb9672f3187f`, `8b965134cef7`. Where the section-4 rejection
of unresolvable addresses bites - the vendor's `CMDQ_SPR_FOR_TEMP` detour - is stated in
`KNOWN-ISSUES.md` 14, not smoothed over here.

## 4. The PA → subsys-id table is device-tree data we already landed

`cmdq_core_subsys_from_phys_addr()` (`v3/cmdq_helper_ext.c:2515`) walks `cmdq_dts_data.subsys[]` comparing
`physAddr & mask == msb`, and returns `CMDQ_SPECIAL_SUBSYS_ADDR` (99, `cmdq_def.h:24`) when nothing matches.
That table is filled from the `gce` node, and **patch 0070 already landed that node**: `arch/arm64/boot/dts/
mediatek/mt6768.dts:1436` carries 31 `<msb id mask>` triples. Applying the table to the 12 module addresses in
the landed `ddp_info.c` table:

    mutex0/ovl0/rdma0/wdma0/color0 (0x1400_1000…0x1400_f000) → id 1  (mmsys_config_base)
    ccorr0/aal0/gamma0/dither0/rsz0 (0x1401_0000…0x1401_5000) → id 2  (disp_dither_base)
    pwm (0x1100e000) → NO usable entry: pwm_sw_base = <0x1100e000 99 0xffff0000>, i.e. the vendor's own DT
                       marks it 99 = CMDQ_SPECIAL_SUBSYS_ADDR, the "not in my subsys table" value

Every address the landed objects can actually produce resolves to a 5-bit id (1 or 2), and the one that does not
is flagged special **by the stock DT itself** - so the ASSIGN-into-GPR fallback at `cmdq_record.c:898-908` is
not needed by anything currently landed. That matters because it is the one place the two encodings are *not*
the same word: the vendor puts a `CMDQ_LOGIC_ASSIGN << 16` selector there where mainline's `cmdq_pkt_assign()`
puts `reg_dst`. Whether the MT6768 GCE accepts mainline's LOGIC layout is a question for the GCE programmer's
guide or hardware, and this port declines to answer it by preferring neither encoding: the design simply does
not need the path yet.

## 5. The `mediatek,gce` arbitration question, answered for this layer

It was left open on the theory that the record layer might contend with a mainline GCE driver for the node.
Measured, there is no contention today, for two independent reasons:

* `drivers/mailbox/mtk-cmdq-mailbox.c:673` matches only `mediatek,mt8173-gce`, `mt8183-gce`, `mt6779-gce`,
  `mt8192-gce`, `mt8195-gce`. Our node is `compatible = "mediatek,gce", "syscon"`, so nothing binds it, and
* the node has **no `#mbox-cells`**, so even a matching driver could not be asked for a channel by a client.
  Its 176 lines are data: 31 subsys triples plus per-engine `mboxes`/`disp_*`/`vdec*` lists the vendor's own
  driver parses. Nothing maps its `reg = <0 0x10238000 0 0x4000>`.

Which is also the design's hard limit, and it is a more interesting answer than "who owns the MMIO": **the
record layer cannot be exercised until a mailbox provider binds that node**, because `cmdq_pkt_write_s_value()`
needs a `struct cmdq_pkt *`, `cmdq_pkt_create()` needs a `struct cmdq_client`, and a client needs
`mbox_request_channel_byname`/`mbox_request_channel` against a provider. A `cmdqRecWrite` adapter landed alone
would therefore be code with no path to a working `handle` - and if it silently dropped writes instead, it would
be the exact CPU-substitute fabrication this project has already rejected twice.

## 6. Recommendation: what to land, and with what

Not a 4-function slice. The measurement chain says the record layer and the GCE binding are one dependency:

1. **`cmdqBackup{Allocate,Read,Write,Free}Slot` + its backing store can land alone.** In v3 these are *not*
   GCE backup registers: `cmdqBackupAllocateSlot` is `cmdq_alloc_mem` (`cmdq_record.c:3948` → `:2004`) which is
   `cmdqCoreAllocWriteAddress(count, &pa, CMDQ_CLT_DISP)` → `cmdq_core_alloc_hw_buffer_clt(cmdq_dev_get(), …)`
   (`cmdq_helper_ext.c:1996`), i.e. a **coherent buffer whose PA is the handle**, plus a global
   `cmdq_ctx.writeAddrList` guarded by `cmdq_write_addr_lock` so `cmdqCoreReadWriteAddress(pa)` can find the VA
   again (`:2072`, list walk + `va + offset`). Reading and writing a slot from the CPU is pure memory access; no
   mailbox, no `reg` mapping, no channel. `ddp_drv.c` calls all three at init and in `disp_get_ovl_bandwidth()`,
   so a CPU-visible pool is exactly what the callers mean.
   (Correction from the implementation: this paragraph proposed obtaining a `struct device` for the DMA API via
   `of_find_device_by_node()` on the gce/syscon node. That step is **not** in the vendor path - `cmdqCoreAllocWriteAddress`
   (`cmdq_helper_ext.c:1996`) just does `alloc_pages()` and hands out `page_to_phys()` as the handle, with no
   device and no DMA API at all - so adding one would have been the same kind of speculation this design forbids
   elsewhere. Landed 0088 therefore has no device lookup, and the pool is `__get_free_pages`-class memory, not a
   `dma_alloc_coherent()` buffer. Also note `cmdqBackupFreeSlot` is *not* in the landed set: `nm -u` finds no
   reference to it anywhere in the 15 objects, so it stays out under the no-speculative-code rule.
   Still open here, and it is a hardware question: whether the GCE on this board addresses that pool directly
   (PA) or through M4U/SMI (IOVA), and therefore whether the *slot values the GCE writes later* land in the
   same memory. Nothing in the landed set has the GCE write to a slot, so this can stay a recorded unknown.
2. **`cmdqRecWrite` lands with the slice that makes a packet possible** - the GCE mailbox binding (a compatible
   string + `#mbox-cells` on the node, or a port-local provider). Its implementation is then the two-line
   adapter of §3 plus the DT table lookup of §4, and its gate is "the 15 objects compile *and* `undeps` loses
   the name". Refusing to land it earlier is the difference between a port and a shim.
3. Keep `CONFIG_MTK_DISP_BRINGUP` off by default throughout. (Correction from the implementation: the proposed
   own symbol - `MTK_CMDQ_DISP_RECORD`, default n, `depends on MTK_CMDQ && OF` - was measured and rejected.
   `CONFIG_MTK_CMDQ` is not set in the config of record at all, so `depends on MTK_CMDQ` would make the provider
   permanently invisible (the mainline helper builds through `drivers/misc/mediatek/cmdq/…`, `drivers/soc/mediatek/Makefile:20`
   `obj-$(CONFIG_MTK_CMDQ_MBOX)`), and a `default MTK_DISP_BRINGUP` on the new symbol is inert against an explicit
   `# CONFIG_MTK_DISP_BRINGUP is not set` in `.config` - 0084-0086's dead-code failure mode, discovered from the
   opposite direction - while `select` propagates but can never force the object off again. Landed 0088 adds no
   symbol and keys its `obj-` line directly on `CONFIG_MTK_DISP_BRINGUP`, which is what "enabled exactly when the
   display core is enabled" means operationally.) If the record code lives in
   `mtk-cmdq-helper.c`, gate the *object* (`obj-$(CONFIG_MTK_CMDQ_DISP_RECORD) += mtk-cmdq-disp-record.o`) in a
   new file rather than growing the mainline file's body, which keeps the mainline CMDQ stack coherent as the
   standing constraint requires and keeps the diff reviewable.
4. Verification for that slice, before it lands: the whole-tree gate with `--link` (`l2-slice-gate.sh` now has
   it), expecting 0 undefined references with the switch off *and* with it on the count dropping by exactly the
   symbols provided, `nm` on both passes, and `undeps.py` re-run. No functional claim without a device.

## 7. Corrections this design makes to earlier notes

* "the vendor's `cmdq_pkt_write(pkt, struct cmdq_base *clt_base, …)` vs mainline's 4-arg" - the dispsys path
  does not go through `cmdq_pkt_write` at all; it goes through `cmdq_op_write_reg` → `WRITE_S`. The comparison
  that matters is `WRITE_S`, and there the answer is that mainline already has it (`write_s_value`,
  `write_s_mask_value`, `cmdq_pkt_assign`, `CMDQ_CODE_MASK`).
* "`enum cmdq_code` is missing 12 values, so a chunk of the vendor engine must come along": for the landed
  need, zero. `WRITE_S`/`WRITE_S_MASK`/`MASK`/`LOGIC`/`EOC` are already in our ported header. `MOVE` is not
  reached except via the mask, which mainline implements with `MASK`.
* "the `mediatek,gce` DT-node arbitration" is not a conflict today - nothing binds the node and it has no
  `#mbox-cells` - but it *is* the reason the record half cannot be landed first. That reframing is the most
  useful thing this document produced.
* The backup slots are memory, not registers: no GCE MMIO anywhere in the CPU path of
  `cmdqBackup{Allocate,Read,Write}Slot`.

## 8. Reassessment after 0088 (measured in `buildpub`/`buildfull`, this round)

Directive item 3 asked whether the deferred `cmdqRecWrite` is still required, now that the callsites were actually
read rather than counted. Answer: **required at link time, unreachable at runtime, and unchanged in design.**

* `nm -u` on the 15 landed display objects: 502 undefined-reference lines remain (507 at the 0087 tip - the three
  slot names are now provided), of which 29 are `cmdqRecWrite`, from `ddp_mutex.o` and `ddp_rsz.o`.
* Those two objects are not dead weight: of the 11 symbols they define (`nm T`), 9 are referenced by `ddp_manager.o`,
  so the mutex layer is live inside the landed set.
* But nothing creates a record: `nm -u` finds 0 references to `cmdqRecCreate`/`cmdqRecDestroy`, and
  `ddp_manager.c` only forwards the `struct cmdqRecStruct *cmdqhandle` it was *given* (`:49`, `:415`, `:545`;
  calls at `:553`, `:556`, `:681`, …). `DISPSYS_SLOT_BASE` is not a constant base either - it is
  `#define DISPSYS_SLOT_BASE dispsys_slot` (`ddp_reg.h:115`), the global the allocator fills - so reads do use the
  allocated pool, and a near-miss claim that the port "reads a constant base" was checked and rejected.
* Therefore the next consumer that would execute a record is `ddp_dsi`/the config layer, i.e. the DSI slice
  (deferred by decision 135), and the GCE mailbox binding question stays exactly where §5 left it: to be answered
  from stock evidence about the vendor gce node, not by inventing `#mbox-cells`, a compatible string or a
  port-local provider.
* `DISP_SLOT_NUM` is 5 (`ddp_hal.h:88-94`), so `disp_probe_1()` (`ddp_drv.c:499`, inside the function starting at
  `:424`) allocates 20 B from a one-page minimum - the pool is generously sized, and the range-based lookup's
  missing index bound is a real but currently unreached hazard, which the host harness reproduces on both sides
  rather than papering over (`tests/mtk_disp_slot_host_check.c`, 37 cases / 0 mismatches,
  `report/mtk-disp-slot-check.txt`).
* Methodology note worth carrying: the harness case for that hazard *passed while proving nothing* in its first
  version, because stock and port shared one bump arena and were interleaved, so the aliased slot landed in a pool
  nobody asserted on. A test that claims an observable must assert the observable (the neighbour pool contains the
  written value on both sides), not merely that two implementations agree.
