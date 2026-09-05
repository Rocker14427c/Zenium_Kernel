# The record-layer fork: three shapes, measured (2026-09-05)

The landed display core needs exactly 4 CMDQ record symbols (`cmdqRecWrite`,
`cmdqBackupAllocateSlot`, `cmdqBackupReadSlot`, `cmdqBackupWriteSlot`); the *full* display chain needs
31 record entry points at 453 callsites in 12 files, and they are live on this board (guard-resolved
census, no `CONFIG_MTK_SEC_VIDEO_PATH_SUPPORT` escape). All of them are defined in ONE vendor file,
`drivers/misc/mediatek/cmdq/v3/cmdq_record.c` (4,140 lines), which pulls in **no** other v3 engine file.
So the question is not "how much of the engine" - it is **who owns `struct cmdq_pkt` and the packet
buffer**, because that is the only wall the record file hits (159 error lines, all of them
`pkt->` members mainline lacks or `cmdq_code` values mainline lacks).

Standing constraints this has to satisfy: keep mainline's `mtk-cmdq.h`/CMDQ stack coherent; every added
symbol defined exactly once; preserve stock CMDQ semantics; no speculative API shims; do not carry the
whole v3 engine unless a live display callsite proves it required; never claim behaviour not exercised
on hardware.

| | A. extend mainline's CMDQ ABI, carry `cmdq_record.c` | B. carry the vendor v3 engine | C. defer, land CMDQ-free layers first |
|---|---|---|---|
| what | Add the 6 `struct cmdq_pkt` members + 13 `enum cmdq_code` values to the shared headers (vendor spelling, defined once), make `mtk-cmdq-mailbox.c` initialise them (it already allocates the buffer), then land `cmdq_record.c` + 2 headers with ~22 marked `pkt->` adaptations | Also land `cmdq_driver.c`/`cmdq_device.c`/`cmdq_helper_ext.c`/`cmdq_subsys_common.c`/`cmdq_event_common.c`/`cmdq_virtual.c`/`cmdq_mdp_common.c`/`mt6768/` and convert `drivers/mailbox/mtk-cmdq-mailbox.c` back to the vendor engine interface (i.e. revert 0082) | No record layer yet; land what has no GCE need: `videox/disp_helper.c` wiring, `ddp_dbi.c`/`ddp_dpi.c` (not in stock `obj-y`), non-display leftovers |
| size | 1 vendor .c (4,140 ln) + 2 headers + ~350-500 ln of header/helper delta + ~22 marked adaptations | +17,706 ln of engine .c (26,437 ln if `cmdq_test.c`/`cmdq_sec*.c` come too) + the mailbox conversion 0082 removed | ~1 file + 1 Makefile line |
| hardware risk | the record layer's GCE words are stock vendor code, but they are now generated into a buffer allocated by **mainline's** mailbox driver; the buffer size/`avail_buf_size` policy has to match mainline's `cmdq_pkt` allocation or GCE tasks truncate | zero new semantics: everything is stock, including the task pools - BUT `cmdq_driver.c` registers its own platform driver on the **same `mediatek,gce` DT node** mainline's mailbox driver binds, so one of the two must stop binding it. That is a boot-level change for every CMDQ client (SMI, and any mainline driver using the mailbox) | none, but the display chain still cannot link, so "flash-ready" is not reached |
| against the constraints | grows the shared ABI 0082 protects; `buf` vs `va_base` is a rename of a mainline-visible field, which every mainline CMDQ user then compiles against | contradicts "do not carry the whole engine" as measured (the record layer needs 0 of it), and re-opens the incoherence 0082 closed | satisfies everything, decides nothing |
| path to a working display | needs `ddp_dsi.c`/`ddp_ovl.c`/`ddp_rdma_ex.c`/`ddp_wdma_ex.c`/`ddp_path.c`/`ddp_mmp.c` on top (104 more record callsites, all satisfiable by the same 31 entry points) | same, plus the BDG/sleep families become available verbatim | not reachable by deferral alone |

## What the measurement favours, stated as a recommendation, not a decision

A, in that exact scope, is the only option that both keeps a single packet model (0082's purpose) and
lands stock record code. Two things must be true before it is honest, and both are gates rather than
hopes:

1. **`buf` must not become a second buffer.** mainline's `struct cmdq_pkt` has `va_base`/`pa_base` and
   allocates through `cmdq_mbox_create()`; the vendor `buf`/`avail_buf_size` pair must be *aliases or
   initialisations of the same allocation*, not a second `kmalloc`. If they are two buffers, GCE tasks
   are submitted from one and written into the other, which is a black screen that still compiles - the
   worst failure mode available here. Measurable offline: compare `pkt->cmd_buf_size`'s producer in
   mainline with `CMDQ_CMD_BUFFER_SIZE`'s use in the vendor, and write a host harness for the encoder
   like the 48/0 word check in L1 (that method already worked).
2. **13 opcodes must be added exactly as the vendor encodes them**, with the L1 word-encoding harness
   extended to cover `WRITE_S_W_MASK`, `SET_TOKEN`/`CLEAR_TOKEN`, `WAIT_NO_CLEAR`, `JUMP_C_*`,
   `PREFETCH_*`, `MOVE`/`RAW`. Anything the harness cannot pin down is a hold, not a guess.

If either gate fails, the fallback is B with `CONFIG_MTK_CMDQ_MBOX` turned off for mainline's binder -
and B's DT-node arbitration has to be written down as a board-level change, because it affects SMI
timing and every other mailbox client on this SoC.

C is not a third architecture; it is the same fork postponed, and the `disp_helper.c` line is owed in
every branch, so it is the only work that is safe to do while this is undecided.
