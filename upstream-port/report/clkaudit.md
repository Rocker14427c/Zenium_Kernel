# Clock provider audit - mt6768.dtb vs clk-mt6768.c+clk-mt6768-pg.c

Per provider domain: ids the ported driver registers, and how the device's
own clock references classify against the header + driver.

| domain | ids registered by driver | refs | registered | header id, not registered | foreign numbering | unresolved provider |
|---|---|---|---|---|---|---|
| CLK_APMIXED | 20 | 4 | 4 | 0 | 0 | 0 |
| CLK_AUD | 12 | 8 | 8 | 0 | 0 | 0 |
| CLK_CAM | 9 | 9 | 9 | 0 | 0 | 0 |
| CLK_GCE | 1 | 0 | 0 | 0 | 0 | 0 |
| CLK_IMG | 5 | 5 | 5 | 0 | 0 | 0 |
| CLK_INFRA | 86 | 70 | 70 | 0 | 0 | 0 |
| CLK_MFG | 1 | 1 | 1 | 0 | 0 | 0 |
| CLK_MM | 32 | 37 | 37 | 0 | 0 | 0 |
| CLK_PERI | 1 | 0 | 0 | 0 | 0 | 0 |
| CLK_TOP | 135 | 65 | 65 | 0 | 0 | 0 |
| CLK_VDEC | 4 | 2 | 2 | 0 | 0 | 0 |
| CLK_VENC | 3 | 4 | 4 | 0 | 0 | 0 |
| None | 1 | 6 | 17 | 0 | 0 | 0 |
| SCP_SYS | 13 | 23 | 23 | 0 | 0 | 0 |

Totals: {"refs": 234, "registered": 234, "header_id_not_registered": 0, "foreign_numbering": 0, "unresolved_provider": 0, "cross_domain_name_collisions": 0}

Two counting notes, both of which have caused misreadings: zero-cell
providers (fixed clocks) are added to the classified column but not to
`refs`, so `registered` can exceed `refs` for a domain; and a domain is
chosen by the *provider* node's compatible, so the same numeric cell means
different things in `CLK_INFRA` (a gate index) and in `SCP_SYS` (a
`scp_clks[].id` power-gate slot) - never compare cell numbers across rows.

`SCP_SYS` is not a clock-gating domain: it is the MTCMOS power-gate
provider that `clk-mt6768-pg.c` registers on the `mediatek,scpsys` node,
with `scp_clks[].id` as the cell index and `SCP_SYS_*` ids from the same
header as the clock ids.

## References whose provider the audit cannot attribute

Provider node not in PROVIDER_DOMAIN: each row is one DT clock cell that
no ported provider claims. This list, not the count, is the work queue.

| consumer | provider node | cell |
|---|---|---|
(none - every DT clock cell in this DTB resolves to a provider the
given driver files register.)
