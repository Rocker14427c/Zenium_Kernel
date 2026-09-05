# Gate 1 result: option A does not survive measurement (2026-09-05)

Asked and answered: *can `struct cmdq_pkt` be extended so the vendor record layer keeps writing through
one packet buffer that mainline's mailbox driver owns - and specifically, can the vendor's `pkt->buf` /
`pkt->avail_buf_size` pair be an alias or an initialisation of mainline's allocation rather than a
second buffer?* The instruction was: if this gate fails, stop and report - do not switch to carrying the
vendor engine, do not land a partially-proven record layer. It failed. No display file was landed from
this probe; the published series is still 0084.

## What the record layer actually does with the packet

`cmdq_record.c` does not go through mainline's packet helpers; it keeps its own cursor over a **list** of
buffer chunks, all of which live in the vendor's `struct cmdq_pkt`:

    include/linux/mailbox/mtk-cmdq-mailbox.h (vendor, 279 ln)   include/linux/mailbox/mtk-cmdq-mailbox.h (ours, 93 ln)
      struct cmdq_pkt {                                            struct cmdq_pkt {
        struct list_head   buf;   <-- chunk list                     void  *va_base;   <-- one buffer
        size_t   avail_buf_size, buf_size, cmd_buf_size;             u32   cmd_buf_size, buf_size;
        struct   { pool, *cnt, *limit } cur_pool;                    struct cmdq_client *cl;
        struct device *dev; u32 priority; bool loop; ...         }
      }

and the three functions that maintain it, in the vendor's `drivers/soc/mediatek/mtk-cmdq-helper.c`:

* `cmdq_pkt_alloc_buf()` (:379) takes a chunk from `pkt->cur_pool.pool` - a **mailbox-engine-owned DMA
  pool** (`struct client_priv.buf_pool`, `buf_cnt`, `pool_limit`) - else falls back to
  `cmdq_mbox_buf_alloc(pkt->dev, &buf->pa_base)`, then `list_add_tail(&buf->list_entry, &pkt->buf)` and
  bumps `avail_buf_size`/`buf_size` by `CMDQ_CMD_BUFFER_SIZE`.
* `cmdq_pkt_add_cmd_buffer()` (:450) chains: when a chunk is full it allocates the next, copies the last
  instruction to the new chunk's head, and **patches a `CMDQ_CODE_JUMP` absolute instruction into the old
  chunk** (`((u64)(CMDQ_CODE_JUMP << 24 | 1) << 32) | (CMDQ_REG_SHIFT_ADDR(buf->pa_base) & 0xFFFFFFFF)`),
  using the chunk's **physical** address.
* `cmdq_pkt_get_va_by_offset()` (:565) walks the list to map an offset to a VA.

Mainline 5.15 has none of this. Its `cmdq_pkt_create()` (our
`drivers/soc/mediatek/mtk-cmdq-helper.c:112`) is `kzalloc(size)` + `dma_map_single()` into
`pkt->va_base`/`pa_base`, one buffer, and submission copies that one range into the mbox message. There
is no list to alias, no `avail_buf_size`, no pool, and no second-chunk jump path: `pkt->buf` cannot be an
alias because the *submission* buffer in the vendor design **is** the list. So the choice is not "alias
or second buffer"; it is "one buffer model or the vendor's".

## What option A therefore costs

It is not "extend a header and land one file". Making `cmdq_record.c` compile *and submit correctly*
requires the vendor's client **and** mailbox stack, because the chunk allocator, the pool handle
(`client_priv`), `cmdq_mbox_buf_alloc` and the GCE-visible address of every chunk all live there:

| file | ours now | vendor | delta |
|---|---|---|---|
| `drivers/soc/mediatek/mtk-cmdq-helper.c` | 654 | 2,521 | +1,867 |
| `drivers/mailbox/mtk-cmdq-mailbox.c` | 705 | 2,525 | +1,820 |
| `include/linux/soc/mediatek/mtk-cmdq.h` | 298 | 434 | +136 |
| `include/linux/mailbox/mtk-cmdq-mailbox.h` | 93 | 279 | +186 |
| `drivers/misc/mediatek/cmdq/v3/cmdq_record.c` | not landed | 4,141 | +4,141 |

≈ 4,000 lines of vendor C in the two files 0082 deliberately reverted, ~320 lines of shared-header ABI,
plus the ~22 marked `pkt->` adaptations in the record file. The earlier "26,437 lines of v3 engine are not
required" finding still holds - `cmdq_record.c` references no global defined in another v3 `.c` - but it
is no longer the binding constraint; the mailbox/helper buffer stack is. That was not known when option A
was costed at "~350-500 lines of header/helper delta" in `l2-record-layer-options.md`; that estimate is
superseded by the table above.

## The part that cannot be verified offline at all

The chunks the GCE executes are allocated by the *mailbox driver for the engine*, and the jump-patch
embeds `buf->pa_base` after `CMDQ_REG_SHIFT_ADDR`. On MT6768 the address the GCE must be given is the
one its SMMU/M4U context resolves, and the vendor obtains it from its own `cmdq->dev`/`cmdq->dma_pa`
machinery (`mtk-cmdq-mailbox.c:1986`) under `CONFIG_MTK_CMDQ_MBOX_EXT`-adjacent code paths; our tree has
`MTK_CMDQ_MBOX_EXT=n` (like `even_defconfig`) and mainline's mailbox has no such concept. So the question
"is the page I hand the GCE the page the GCE reads?" would be answered here by **first boot on the device**
- which is exactly the class of failure the standing rules refuse to let me paper over: wrong encoding or
wrong address is a black panel or a corrupted display at vblank, and a successful compile would prove
nothing. A mainline-client-only variant (keep one buffer, cap a record task to one chunk, never chain)
would compile and would be *wrong* for the 6 files whose real tasks exceed a chunk, so it is excluded as
behaviour invention rather than porting.

## Where that leaves the port, precisely

* Landed and re-verified: 0084, tree `3fa1c650082e917773ac00d2190befb35d575572`, 14/14 objects, 0
  duplicate link-visible definitions, environment rebuilt and its recipe fixed (see
  `l2-recovery-and-record-probe.md` s1). The display core stays **compile-verified, not linkable**.
* 70 names have no provider in the tree; 4 of them are the record quartet that this gate was about, and
  they are *not* provided by an ABI extension - they need the vendor CMDQ client+mailbox stack.
* One dependency-order item is safe and remains owed regardless of the choice:
  `video/mt6768/videox/disp_helper.c` is in the tree but built by nothing (3 unresolved names).
* The remaining decision is now between **B** (carry the vendor CMDQ stack: engine-side buffer pool, and
  `cmdq_driver.c` registering on the same `mediatek,gce` node mainline's mailbox binds - a
  boot-level arbitration that also touches SMI) and **stopping the display port at the honest substrate it
  has now reached** (dispsys core + M4U/SMI + a single-API CMDQ, all compile-verified, no claim of a
  working display). I have not begun either.
