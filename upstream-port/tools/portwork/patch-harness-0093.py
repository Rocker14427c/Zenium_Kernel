#!/usr/bin/env python3
"""patch-harness.py - extend tests/mtk_disp_record_host_check.c with the read-to-data-register section.

Every edit asserts its anchor: if the file has moved, this stops instead of producing a harness that
quietly tests less than it claims.
"""
import sys

P = "/home/user/Zenium_Kernel/upstream-port/tests/mtk_disp_record_host_check.c"
s = open(P).read()


def sub(old, new, count=1):
    global s
    n = s.count(old)
    if n != count:
        sys.exit("ANCHOR %r: expected %d, found %d" % (old[:70], count, n))
    s = s.replace(old, new, count)


sub("""/* the five instruction numbers the two sides use */
struct ops {
	unsigned int mask, move, write_s, write_s_mask, write_s_w_mask;
};

static const char *const op_names[5] = {
	"CMDQ_CODE_MASK", "CMDQ_CODE_MOVE", "CMDQ_CODE_WRITE_S",
	"CMDQ_CODE_WRITE_S_MASK", "CMDQ_CODE_WRITE_S_W_MASK",
};""",
"""/*
 * The instruction numbers the two sides use, read out of the headers rather than typed. The last
 * two are here for the read-to-data-register entry point and they stay asymmetric on purpose:
 * mainline's 5.15 mailbox header has CMDQ_CODE_READ_S (0x80, the number the vendor's v3 path emits)
 * and no CMDQ_CODE_READ at all, which is the measured reason cmdqRecReadToDataRegister() implements
 * the below-CMDQ_DATA_REG_JPEG_DST case and refuses the other one. load_ops() leaves anything it
 * cannot find at 0xdeadbeef and the printer shows that as "absent", so the asymmetry is reported
 * rather than asserted away.
 */
struct ops {
	unsigned int mask, move, write_s, write_s_mask, write_s_w_mask;
	unsigned int read_s, read;
};

static const char *const op_names[7] = {
	"CMDQ_CODE_MASK", "CMDQ_CODE_MOVE", "CMDQ_CODE_WRITE_S",
	"CMDQ_CODE_WRITE_S_MASK", "CMDQ_CODE_WRITE_S_W_MASK",
	"CMDQ_CODE_READ_S", "CMDQ_CODE_READ",
};

/* the two numbers cmdq_op_read_to_data_register() branches on, from v3 cmdq_def.h */
struct gpr_ops {
	unsigned int offset, jpeg_dst, pq_color;
};""")

sub("""	unsigned int *field[5] = { &o->mask, &o->move, &o->write_s,
				   &o->write_s_mask, &o->write_s_w_mask };""",
"""	unsigned int *field[7] = { &o->mask, &o->move, &o->write_s,
				   &o->write_s_mask, &o->write_s_w_mask,
				   &o->read_s, &o->read };""")
sub("""	for (i = 0; i < 5; i++) {
		char pat[96];
		const char *p;""",
"""	for (i = 0; i < 7; i++) {
		char pat[96];
		const char *p;""")
sub("""	for (i = 0; i < 5; i++) {
		unsigned int p = (&po.mask)[i], v = (&vo.mask)[i];""",
"""	for (i = 0; i < 7; i++) {
		unsigned int p = (&po.mask)[i], v = (&vo.mask)[i];""")

sub("""struct addr_case {""",
"""/* CMDQ_GPR_V3_OFFSET and the two data registers, from a tree's v3 cmdq_def.h */
static void load_gpr(const char *root, struct gpr_ops *g)
{
	char path[512];
	static const char *const names[3] = { "define CMDQ_GPR_V3_OFFSET",
		"CMDQ_DATA_REG_JPEG_DST =", "CMDQ_DATA_REG_PQ_COLOR =" };
	unsigned int *field[3] = { &g->offset, &g->jpeg_dst, &g->pq_color };
	char *text;
	int i;

	snprintf(path, sizeof(path),
		 "%s/drivers/misc/mediatek/cmdq/v3/cmdq_def.h", root);
	text = slurp(path);
	if (!text) {
		for (i = 0; i < 3; i++)
			*field[i] = 0xdeadbeef;
		return;
	}
	for (i = 0; i < 3; i++) {
		const char *p = strstr(text, names[i]);

		*field[i] = 0xdeadbeef;
		if (!p)
			continue;
		p += strlen(names[i]);
		while (*p == ' ' || *p == '\\t')
			p++;
		if (*p == '(')
			p++;
		if (sscanf(p, " %i", field[i]) != 1)
			*field[i] = 0xdeadbeef;
	}
	free(text);
}

struct addr_case {""")

sub("""	printf("\\n%d cases, %d mismatches\\n", cases, mismatches);""",
"""	/*
	 * cmdqRecReadToDataRegister(): the vendor's rules from cmdq_op_read_to_data_register()
	 * (v3/cmdq_record.c:1576-1600) plus the read half of cmdq_append_rw_s_command()
	 * (:941-951) against mainline's struct cmdq_pkt image, for every address this tree can
	 * produce and the registers on both sides of the JPEG_DST boundary. The vendor's arg_type is
	 * (value_type << 2) | (addr_type << 1) with value type 1 and address type 0, so 1 << 2; the
	 * port's equivalent is dst_t at bit 7 of its subsys byte, which is the same bit 23 of arg_a.
	 */
	{
		static const u32 regs[] = { 0x00, 0x04, 0x10, 0x11, 0x13, 0x1f };
		struct gpr_ops pg, vg;
		char *rec_c = NULL, *rec_h = NULL;
		bool refuses_special = false;
		u32 k;

		snprintf(path, sizeof(path),
			 "%s/drivers/soc/mediatek/mtk-cmdq-disp-record.c", tree);
		rec_c = tree ? slurp(path) : NULL;
		snprintf(path, sizeof(path),
			 "%s/drivers/misc/mediatek/cmdq/v3/cmdq_record.h", tree);
		rec_h = tree ? slurp(path) : NULL;
		refuses_special = rec_c &&
			strstr(rec_c, "static s32 mtk_disp_rec_resolve_subsys(") &&
			strstr(strstr(rec_c, "static s32 mtk_disp_rec_resolve_subsys("),
			       "id == MTK_DISP_REC_SUBSYS_SPECIAL") &&
			strstr(strstr(rec_c, "static s32 mtk_disp_rec_resolve_subsys("),
			       "return -EINVAL");

		load_gpr(tree, &pg);
		if (vendor)
			load_gpr(vendor, &vg);
		else
			memset(&vg, 0xff, sizeof(vg));

		printf("\\ncmdqRecReadToDataRegister: the numbers, read from both trees\\n");
		for (i = 0; i < 7; i++) {
			unsigned int p = (&po.mask)[i], v = (&vo.mask)[i];
			char vb[16];

			if (v == 0xdeadbeef)
				snprintf(vb, sizeof(vb), "absent");
			else
				snprintf(vb, sizeof(vb), "0x%02x", v);
			printf("  %-28s port=0x%02x vendor=%s\\n", op_names[i], p, vb);
		}
		printf("  %-28s port=0x%x vendor=0x%x\\n", "CMDQ_GPR_V3_OFFSET",
		       pg.offset, vg.offset);
		printf("  %-28s port=0x%x vendor=0x%x\\n", "CMDQ_DATA_REG_JPEG_DST",
		       pg.jpeg_dst, vg.jpeg_dst);

		snprintf(detail, sizeof(detail),
			 "port 0x%x, vendor 0x%x; the vendor adds it inside its op, so the entry point does and no callsite does",
			 pg.offset, vg.offset);
		report("CMDQ_GPR_V3_OFFSET is one number in both trees",
		       pg.offset != 0xdeadbeef && pg.offset == vg.offset, detail);
		snprintf(detail, sizeof(detail), "port 0x%x, vendor 0x%x", pg.jpeg_dst,
			 vg.jpeg_dst);
		report("the branch boundary is one number in both trees",
		       pg.jpeg_dst != 0xdeadbeef && pg.jpeg_dst == vg.jpeg_dst, detail);
		snprintf(detail, sizeof(detail), "port 0x%02x, vendor 0x%02x (same number, different header)",
			 po.read_s, vo.read_s);
		report("CMDQ_CODE_READ_S is 0x80 on both sides",
		       po.read_s == 0x80 && po.read_s == vo.read_s, detail);
		{
			char pb[24];

			if (po.read == 0xdeadbeef)
				snprintf(pb, sizeof(pb), "has none");
			else
				snprintf(pb, sizeof(pb), "0x%02x", po.read);
			snprintf(detail, sizeof(detail),
				 "port %s, vendor 0x%02x: with no enumerator there is no mainline helper for it either",
				 pb, vo.read);
		}
		report("the wpr branch's opcode is absent from mainline, so it is refused not faked",
		       po.read == 0xdeadbeef, detail);

		printf("\\ncmdqRecReadToDataRegister: one instruction, both encoders\\n");
		for (i = 0; i < (int)(sizeof(addrs) / sizeof(addrs[0])); i++) {
			for (k = 0; k < (int)(sizeof(regs) / sizeof(regs[0])); k++) {
				u32 reg = regs[k] == 0x04 && pg.pq_color != 0xdeadbeef ?
					pg.pq_color : regs[k];
				u32 subsys = (u32)addrs[i].want;
				u64 vw, pw;

				if (reg == 0xdeadbeef || reg >= pg.jpeg_dst)
					continue;
				snprintf(detail, sizeof(detail), "%s, reg 0x%02x", addrs[i].what,
					 reg);
				if (subsys == MTK_DISP_REC_SUBSYS_SPECIAL) {
					s32 got = mtk_disp_rec_core_subsys_from_phys_addr(
						tbl, CMDQ_SUBSYS_MAX_COUNT, addrs[i].addr);

					snprintf(detail, sizeof(detail),
						 "%s, reg 0x%02x: the shared model returns %d (no gce row covers it) and mtk_disp_rec_resolve_subsys() turns that into -EINVAL, so no word is built (the vendor's cmdq_get_subsys_id() has no such refusal)",
						 addrs[i].what, reg, got);
					report("address no gce row covers is refused, not encoded",
					       got == MTK_DISP_REC_SUBSYS_SPECIAL &&
						       refuses_special, detail);
					continue;
				}
				vw = mtk_disp_rec_inst_word(vo.read_s,
					mtk_disp_rec_pack_arg_a(reg + pg.offset, subsys, 1u << 2),
					(u32)((addrs[i].addr & MTK_DISP_REC_ADDR_MASK) << 16));
				pw = port_word((u8)po.read_s, (u16)(reg + pg.offset),
					       (u8)(subsys | (1 << 7)),
					       (u32)((addrs[i].addr & MTK_DISP_REC_ADDR_MASK) << 16));
				snprintf(detail, sizeof(detail), "%s, reg 0x%02x: vendor 0x%016llx, port 0x%016llx",
					 addrs[i].what, reg, (unsigned long long)vw,
					 (unsigned long long)pw);
				report("read_s word identical, dst_t set, address in arg_b[31:16]",
				       vw == pw, detail);
			}
		}

		/*
		 * What the file says, not what a reader hopes it says. port_c above is freed by the
		 * subsys-table section, so this reads its own copies.
		 */
		if (rec_c) {
			const char *body = strstr(rec_c,
				"cmdqRecReadToDataRegister(struct cmdqRecStruct *handle, u32 hw_addr,");
			bool delegates = body && strstr(body, "cmdq_pkt_read_s(pkt,");
			bool refuses = body && strstr(body, "-EOPNOTSUPP") &&
				       strstr(body, "CMDQ_DATA_REG_JPEG_DST)");
			bool adds = body && strstr(body, "CMDQ_GPR_V3_OFFSET");
			bool resolves = body && strstr(body, "mtk_disp_rec_resolve_subsys(hw_addr, &subsys)");

			report("the entry point delegates to cmdq_pkt_read_s() rather than building a word",
			       delegates, delegates ? "no local encoding to get wrong" :
						      "the definition must call the port helper");
			snprintf(detail, sizeof(detail),
				 "the refusal is in the first %d bytes of the definition, where one exists",
				 body ? (int)(strstr(body, "EXPORT_SYMBOL(cmdqRecReadToDataRegister)") - body) : -1);
			report("at or above CMDQ_DATA_REG_JPEG_DST it returns -EOPNOTSUPP",
			       refuses, refuses ? detail : "the wpr branch must not be encoded silently");
			report("only the definition adds CMDQ_GPR_V3_OFFSET", adds,
			       adds ? "so a callsite passing 0x04 cannot double-add it" :
				      "the offset belongs inside the entry point");
			report("the address is resolved before the destination register is looked at",
			       resolves, resolves ? "" : "an unresolvable address should fail first");
			free(rec_c);
		} else {
			report("read entry point source checks", false,
			       "skipped: needs $TREE's mtk-cmdq-disp-record.c");
		}
		if (rec_h) {
			const char *d = strstr(rec_h, "cmdqRecReadToDataRegister(struct cmdqRecStruct *handle, u32 hw_addr,");
			bool typed = d && strstr(d, "enum cmdq_gpr_reg dst_data_reg)");

			snprintf(detail, sizeof(detail), "%s",
				 typed ? "the landed header the callsite includes" : "not found");
			report("the declaration is the vendor's own, landed verbatim at 0085",
			       typed, detail);
			free(rec_h);
		} else {
			report("declaration check", false, "skipped: needs $TREE's cmdq_record.h");
		}
	}

	printf("\\n%d cases, %d mismatches\\n", cases, mismatches);""")

open(P, "w").write(s)
print("harness extended")
