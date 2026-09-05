# The GCE provider/binding question, answered from stock evidence

This is the evidence half of the standing instruction: `cmdqRecWrite` stays deferred until the GCE
provider/binding question is resolved **from stock evidence**, and no speculative `#mbox-cells`,
compatible string or port-local provider is added. The evidence is now gathered - all of it read out of
this repository (the vendor 4.19.325 tree at the root, `arch/arm/boot/dts/mt6768.dts`) and the landed
5.15 tree - so the remaining choice is a decision, not a guess. **Nothing here is implemented.**

## 1. What stock actually does on MT6768

Three separate objects, not two:

| piece | where | what it is |
|---|---|---|
| `gce: gce@10238000` | `arch/arm/boot/dts/mt6768.dts:1424` | `compatible = "mediatek,gce", "syscon"`, `reg = <0 0x10238000 0 0x4000>`, `#clock-cells = <1>`, `interrupts = <GIC_SPI 170 IRQ_TYPE_LEVEL_LOW>`, `disp_mutex_reg = <0x14016000 0x1000>` and 31 `*_base = <pa id mask>` triples (`g3d_config_base = <0x13000000 0 0xffff0000>` … `pwm_sw_base = <0x1100e000 99 0xffff0000>`). **No `#mbox-cells`.** Pure data + syscon. |
| `gce_mbox: gce_mbox@10238000` | `:1601` | `compatible = "mediatek,mt6768-gce"`, *the same* `reg`/`interrupts`, `default_tokens` (7 `/bits/ 16` entries), `clocks = <&infracfg_ao CLK_IFR_GCE>, <&infracfg_ao CLK_IFR_GCE_26M>` / `clock-names = "gce", "gce-timer"`, **`#mbox-cells = <3>`**, `#gce-event-cells = <1>`, `#gce-subsys-cells = <2>`. This is the mailbox **provider** node. |
| `gce_mbox_svp@10238000` | `:1623` | second provider, `compatible = "mediatek,mailbox-gce-svp"`, `#mbox-cells = <3>`, extra `GIC_SPI 171` - inside `#if defined(CONFIG_MTK_SEC_VIDEO_PATH_SUPPORT) || defined(CONFIG_MTK_CAM_SECURITY_SUPPORT)`, so it does not exist in the non-secure build; the client's threads 8-10 switch to it under the same `#if` (`:1580-1589`). |

The display CMDQ client node (`:1572` area) carries `mediatek,mailbox-gce = <&gce_mbox>`,
`secure_thread = <6 8>` and 15 `mboxes = <&gce_mbox <index> <timeout> <priority>>` entries - the 3 cells
are index / timeout-ms / priority, per the provider's xlate below.

Provider code: the vendor's `drivers/mailbox/mtk-cmdq-mailbox.c` is the **same file mainline has**, with a
longer match table that includes MT6768 - `cmdq_of_ids[]` at `:2047` lists `mediatek,mt6768-gce` →
`gce_plat_v2` (`:2053`), and `gce_plat_v2` is `{.thread_nr = 16}`. Its xlate (`:1784`) is 3-cell:

```c
int ind = sp->args[0];
if (ind >= mbox->num_chans) return ERR_PTR(-EINVAL);
thread->timeout_ms = sp->args[1] != 0 ? sp->args[1] : CMDQ_TIMEOUT_DEFAULT;
thread->priority   = sp->args[2];
```

Client-side plumbing on MT6768 does **not** go through the vendor v3 engine's own MMIO: with
`# CONFIG_MTK_CMDQ_MBOX_EXT is not set` and `CONFIG_MTK_CMDQ_MBOX=y` in `arch/arm64/configs/even_defconfig`
(`:1807`, `:4452` - the board's own config of record), the API v3 uses is the plain helper: v3's
`cmdq_helper_ext.c:5367-5390` loops `clt = cmdq_mbox_create(dev, i)` for `i < CMDQ_MAX_THREAD_COUNT`
(v3: 24, or `BIT(5)|24` with secure support, `v3/cmdq_def.h:33-35`), keys the result by
`cmdq_mbox_chan_id(clt->chan)` into a global `cmdq_clients[]`, and **breaks on the first failure** - so on
this SoC the loop stops at the provider's 16 channels. `cmdq_mbox_create()` itself (`drivers/soc/mediatek/mtk-cmdq-helper.c:169`)
is `kzalloc` + `mbox_request_channel(&client->client, index)`: the ordinary mailbox framework, no vendor
extension (`grep -rn "mbox_request_channel" drivers/misc/mediatek/cmdq/` returns nothing, because the call
lives in the helper, not in the engine).

The record APIs are thin wrappers over that: `cmdqRecCreate` (`v3/cmdq_record.c:3808`) → `cmdq_task_create`
(`:374`), which `kzalloc`s a `struct cmdqRecStruct`, sets `engineFlag` from `cmdq_get_func()->flagFromScenario(scenario)`,
takes `cmdq_core_get_controller()` and leaves `thread = CMDQ_INVALID_THREAD`; `cmdqRecWrite` (`:3887`) →
`cmdq_op_write_reg(handle, addr, value, mask)` (the `WRITE_S`/`WRITE_S_W_MASK` + `MASK` path costed in
`l2-record-layer-design-bprime.md` §2-§3, whose encodings are bit-identical to mainline's
`struct cmdq_instruction`).

## 2. What our landed 5.15 tree already has

| fact | value |
|---|---|
| `CONFIG_MTK_CMDQ_MBOX` in the config of record | **`y`** (`.config:7215`) |
| `CONFIG_MTK_CMDQ` | not set (so nothing keys on it) |
| `drivers/soc/mediatek/mtk-cmdq-helper.o` | **built, 104,232 B**, 26 `T` symbols: `cmdq_mbox_create/destroy`, `cmdq_pkt_create/destroy/finalize/flush*`, `cmdq_pkt_write`, `cmdq_pkt_write_mask`, `cmdq_dev_get_client_reg`, `cmdq_pkt_assign`, `cmdq_pkt_poll*`, and - the two that matter here - `cmdq_pkt_write_s_value` (`mtk-cmdq-helper.c:271`) and `cmdq_pkt_write_s_mask_value` (`:285`, which emits `CMDQ_CODE_MASK` with `~mask` then `CMDQ_CODE_WRITE_S_MASK`, i.e. exactly stock's pair) (landed by 0083 + the 0082 revert) |
| `drivers/mailbox/mtk-cmdq-mailbox.o` | built, 123,568 B - the provider exists and is compiled, it just has nothing to bind to |
| `drivers/mailbox/mtk-cmdq-mailbox.c` | present, built, **idle**: `cmdq_of_ids[]` at `:674` matches only `mt8173/mt8183/mt6779/mt8192/mt8195-gce`, and `gce_plat_v2 = {.thread_nr = 16, .shift = 0, .control_by_sw = false, .gce_num = 1}` - the same `thread_nr` as stock's v2 |
| mainline xlate (`:508`) | 2 cells: `ind = args[0]`, `thread->priority = args[1]`; **no timeout cell at all** |
| opcode enum | `include/linux/mailbox/mtk-cmdq-mailbox.h:56-65` in the landed tree: `CMDQ_CODE_MASK = 0x02`, `EOC = 0x40`, `WRITE_S = 0x90`, `WRITE_S_MASK = 0x91`, `LOGIC = 0xa0` - every opcode the §3 adapter needs is already in the tree, none missing |
| our `gce` node | `mt6768.dts:1436`, `compatible = "mediatek,gce", "syscon"`, no `#mbox-cells`, no `gce_mbox` sibling - i.e. the *data* node only, exactly as stock's, and nothing binds it |

So the topology is already half-present: mainline's provider driver and the client helper are in the tree
and compiled; what is missing is the *binding* (a provider node with `#mbox-cells`, and an ID entry mainline
matches), and the display-side API shape (`cmdqRecWrite` vs `cmdq_pkt_write_mask`).

## 3. The three options, costed - none taken

1. **Keep deferring (status quo, zero risk).** The 29 `cmdqRecWrite` link references stay unresolved;
   `ddp_mutex.o`/`ddp_rsz.o` stay out of the image because `CONFIG_MTK_DISP_BRINGUP` is `n`; nothing on a
   device changes, because nothing in the landed set creates a record (0 references to
   `cmdqRecCreate`/`cmdqRecDestroy`). This costs a link, not a behaviour.
2. **Mirror stock's provider node exactly** - add a `gce_mbox`-shaped sibling node (`"mediatek,mt6768-gce"`,
   same `reg`/`interrupts`, `#mbox-cells = <3>`, `default_tokens`, the two extra `#gce-*-cells`) *and*
   `mediatek,mailbox-gce`/`mboxes`/`secure_thread` on the display client node, then serve `cmdqRecWrite`
   over v3-style clients. Faithful to stock cell-for-cell, but it drags in the v3 task/thread layer
   (`cmdq_get_func()` per-SoC table, `mdp_sync/`, 24-thread client enumeration) - the Option-A territory
   gate 1 already killed - and it duplicates `reg` across two nodes, which is what stock does but which no
   mainline binding document sanctions.
3. **Translate to mainline's binding, which the evidence says is behaviourally the same GCE generation** -
   `#mbox-cells = <2>` on a provider node plus `{.compatible = "mediatek,mt6768-gce", .data = &gce_plat_v2}`
   (one line, and stock's own copy of that driver carries precisely this entry with the identical
   `thread_nr = 16`), then `cmdqRecWrite(handle, pa, value, mask)` becomes the §3 adapter: subsys id from
   the already-landed triples, `pa & 0xffff` offset, `cmdq_pkt_write_s_mask_value()` (already defined and
   exported in the landed helper at `mtk-cmdq-helper.c:285`, so the slice would be a caller, not a new API;
   `cmdq_pkt_write_mask()` is the `mask == ~0` variant). Two deviations from stock, both recorded
   rather than hidden: the per-channel **timeout cell disappears** (mainline has no `timeout_ms` in the
   thread struct, so a stock client that asked for a non-default timeout would get mainline's fixed one),
   and `#mbox-cells` 2 vs 3 changes the meaning of the phandle args, so the DT cannot be copied from stock.

## 4. What is deliberately *not* claimed here

No GCE opcode was executed and no register was poked; none of this was run on a device. Unverified by
measurement, and needing either a device or more stock reading: whether MT6768's GCE thread-priority
encoding in `CMDQ_THR_PRIO_x` maps 1:1 onto mainline's `thread->priority` write; what
`default_tokens`/`max_prefetch_cnt` (`cmdq_config_prefetch`, vendor `:1800`) do to first-frame timing
(mainline reads neither); whether the 24-vs-16 thread truncation is load-bearing for any display scenario
(landed set: no, nothing creates a record); and whether M4U/SMI remapping applies to GCE-written slot
memory, which is the hardware question left open in `l2-record-layer-design-bprime.md` §6.1.

Decision needed from the human, because options 2 and 3 both edit the landed, audited device tree and the
mainline mailbox stack - the standing rule was "no speculative `#mbox-cells`, compatible string or
port-local provider", and while options 2 and 3 are now evidence-backed rather than speculative, either one
is an architecture change to already-published patches (0070's DT transplant and 0082's mailbox revert), not
a slice on top.
