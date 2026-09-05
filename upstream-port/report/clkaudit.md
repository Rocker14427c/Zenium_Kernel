# Clock provider audit - mt6768.dtb vs clk-mt6768.c

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
| None | 1 | 29 | 18 | 0 | 0 | 22 |

Totals: {"refs": 234, "registered": 212, "header_id_not_registered": 0, "foreign_numbering": 0, "unresolved_provider": 22, "cross_domain_name_collisions": 0}
