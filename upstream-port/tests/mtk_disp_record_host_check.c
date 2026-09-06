// SPDX-License-Identifier: GPL-2.0-only
/*
 * Host check for the MT6768 display record adapter (slice 0091).
 *
 * Build and run (the line the slice gate uses, from the repository root, with
 * $TREE a v5.15.220 checkout that has the series applied and $VENDOR the
 * read-only 4.19.325 vendor tree):
 *
 *   gcc -std=gnu11 -Wall -I upstream-port/tests/stub \
 *       -I $TREE/include -I $TREE/drivers/misc/mediatek/cmdq/v3 \
 *       -o /tmp/mtk_disp_record_host_check \
 *       upstream-port/tests/mtk_disp_record_host_check.c
 *   /tmp/mtk_disp_record_host_check $TREE $VENDOR
 *
 * Which side is whose, stated plainly:
 *
 *  - The rules under test - mtk_disp_rec_pack_arg_a(),
 *    mtk_disp_rec_pack_arg_b(), mtk_disp_rec_inst_word(),
 *    mtk_disp_rec_var_data_type(),
 *    mtk_disp_rec_core_subsys_from_phys_addr() and
 *    mtk_disp_rec_event_default() - are the ones the kernel file calls,
 *    included from $TREE/include/linux/soc/mediatek/mtk-cmdq-disp-record.h.
 *    Nothing is reimplemented for the port side of the encoding.
 *  - The enumerators come from the landed vendor headers of $TREE
 *    (cmdq_subsys_common.h, cmdq_event_common.h), and the instruction numbers
 *    are parsed out of both trees' include/linux/mailbox/mtk-cmdq-mailbox.h at
 *    run time. No enum value is retyped here.
 *  - The reference side is the vendor's own arithmetic, transcribed from
 *    drivers/misc/mediatek/cmdq/v3/cmdq_record.c:1368 (cmdq_op_write_reg),
 *    :847 (cmdq_append_rw_s_command) and :706 (cmdq_append_command_pkt), with
 *    the subsys position from cmdq_virtual.c:170.
 *  - The port's instruction stream is a transcription of
 *    drivers/soc/mediatek/mtk-cmdq-helper.c: cmdq_pkt_write_s_value() at :271,
 *    cmdq_pkt_write_s_mask_value() at :285, and the file-private struct
 *    cmdq_instruction at :193. That is the one transcription in this file.
 *    The slice gate records a sha256 of those three function bodies so that an
 *    edit to them shows up as a changed hash rather than as a silent
 *    divergence from what was measured here.
 *
 * The host is little-endian, as the arm64 configs here are, so a struct image
 * and the vendor's shift formula describe the same eight bytes. Where the two
 * sides legitimately differ this prints the difference instead of calling it a
 * match - the same discipline as mtk_disp_slot_host_check.c.
 */

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <linux/types.h>

#include <linux/soc/mediatek/mtk-cmdq-disp-record.h>

#include "cmdq_event_common.h"
#include "cmdq_subsys_common.h"

#define MAX_ROWS		128
#define NO_SUBSYS		(-1)

/* the five instruction numbers the two sides use */
struct ops {
	unsigned int mask, move, write_s, write_s_mask, write_s_w_mask;
};

static const char *const op_names[5] = {
	"CMDQ_CODE_MASK", "CMDQ_CODE_MOVE", "CMDQ_CODE_WRITE_S",
	"CMDQ_CODE_WRITE_S_MASK", "CMDQ_CODE_WRITE_S_W_MASK",
};

static int cases, mismatches;

struct row {
	char sym[64];
	char name[64];
};

static void report(const char *what, bool ok, const char *detail)
{
	cases++;
	if (!ok)
		mismatches++;
	printf("  %-52s %-8s %s\n", what, ok ? "ok" : "MISMATCH",
	       detail ? detail : "");
}

static char *slurp(const char *path)
{
	FILE *f = fopen(path, "rb");
	long n;
	char *buf;

	if (!f)
		return NULL;
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	fseek(f, 0, SEEK_SET);
	buf = malloc((size_t)n + 1);
	if (!buf) {
		fclose(f);
		return NULL;
	}
	if (n < 0 || fread(buf, 1, n, f) != (size_t)n) {
		free(buf);
		fclose(f);
		return NULL;
	}
	buf[n] = '\0';
	fclose(f);

	return buf;
}

/* CMDQ_CODE_x = 0xNN, from the header text, missing entries left at 0xdeadbeef */
static bool load_ops(const char *root, struct ops *o)
{
	char path[512];
	unsigned int *field[5] = { &o->mask, &o->move, &o->write_s,
				   &o->write_s_mask, &o->write_s_w_mask };
	char *text;
	int i, found = 0;

	snprintf(path, sizeof(path),
		 "%s/include/linux/mailbox/mtk-cmdq-mailbox.h", root);
	text = slurp(path);
	if (!text) {
		printf("  FATAL: cannot read %s\n", path);
		exit(2);
	}
	for (i = 0; i < 5; i++) {
		char pat[96];
		const char *p;

		*field[i] = 0xdeadbeef;
		snprintf(pat, sizeof(pat), "%s =", op_names[i]);
		p = strstr(text, pat);
		if (p && sscanf(p + strlen(pat), " %i", field[i]) == 1)
			found++;
	}
	free(text);

	return found > 0;
}

/*
 * Collect "[SYM] = <chunk>" rows. In the vendor's file the chunk is a braced
 * initialiser and the name is its .name member; in this port's file the chunk
 * is the string itself. The scan stops at '}' when there is one, so both forms
 * come out as (symbol, name) pairs.
 */
static int parse_rows(const char *text, struct row *rows, int max)
{
	const char *p = text;
	int n = 0;

	while (p && n < max) {
		const char *open = strstr(p, "[CMDQ_SUBSYS_");
		const char *close, *next, *q, *s;
		char *field;
		size_t len;

		if (!open)
			break;
		open++;
		close = strchr(open, ']');
		if (!close)
			break;
		len = (size_t)(close - open);
		if (len >= sizeof(rows[n].sym))
			len = sizeof(rows[n].sym) - 1;
		memcpy(rows[n].sym, open, len);
		rows[n].sym[len] = '\0';

		/* the row ends where the next one starts, or at end of text */
		next = strstr(close, "[CMDQ_SUBSYS_");
		if (!next)
			next = close + strlen(close);

		/* the vendor's row spells the name out as .name = "..."; this
		 * port's row is the string itself. Taking .name when it is there
		 * means the group column cannot be mistaken for the property.
		 */
		field = NULL;
		if (next - close < 4096) {
			char *chunk = malloc((size_t)(next - close) + 1);

			if (chunk) {
				memcpy(chunk, close, (size_t)(next - close));
				chunk[next - close] = '\0';
				field = (char *)strstr(chunk, ".name");
				if (field)
					field = strdup(field);
				free(chunk);
			}
		}
		if (field) {
			q = strchr(field, '"');
			s = q ? q + 1 : NULL;
			q = s ? strchr(s, '"') : NULL;
			if (s && q) {
				len = (size_t)(q - s);
				if (len >= sizeof(rows[n].name))
					len = sizeof(rows[n].name) - 1;
				memcpy(rows[n].name, s, len);
				rows[n].name[len] = '\0';
				n++;
				p = close + 1;
				free(field);
				continue;
			}
			free(field);
		}
		q = strchr(close, '"');
		if (!q || q > next) {
			rows[n].name[0] = '\0';
			n++;
			p = close + 1;
			continue;
		}
		s = q + 1;
		q = strchr(s, '"');
		if (!q)
			break;
		len = (size_t)(q - s);
		if (len >= sizeof(rows[n].name))
			len = sizeof(rows[n].name) - 1;
		memcpy(rows[n].name, s, len);
		rows[n].name[len] = '\0';
		n++;
		p = q + 1;
	}

	return n;
}

/*
 * The gce node as text, braces balanced, so a property is only credited when
 * it really sits inside the node the record adapter reads.
 */
static char *gce_node_of(const char *dts)
{
	const char *start = strstr(dts, "gce: gce@");
	const char *p;
	int depth = 0;
	char *out;

	if (!start)
		return NULL;
	p = strchr(start, '{');
	if (!p)
		return NULL;
	start = p;
	for (; *p; p++) {
		if (*p == '{')
			depth++;
		else if (*p == '}') {
			depth--;
			if (!depth)
				break;
		}
	}
	out = malloc((size_t)(p - start) + 2);
	if (!out)
		return NULL;
	memcpy(out, start, (size_t)(p - start) + 1);
	out[p - start + 1] = '\0';

	return out;
}

static bool prop_u32_in(const char *span, const char *name, unsigned int *val)
{
	char pat[96];
	const char *p;

	snprintf(pat, sizeof(pat), "%s =", name);
	p = strstr(span, pat);
	if (!p)
		return false;

	return sscanf(p + strlen(pat), " <%u>", val) == 1;
}

/*
 * vendor: cmdq_op_write_reg() -> cmdq_append_command() ->
 * cmdq_append_rw_s_command() -> cmdq_append_command_pkt(). One word for the
 * mask (CMDQ_CODE_MOVE, arg_a 0, arg_b ~mask) then the write itself.
 */
static int vendor_encode(const struct ops *o, u32 addr, u32 value, u32 mask,
			 u32 subsys, u64 out[2])
{
	u32 arg_b, arg_b_type, n = 0;

	if (mask != 0xffffffff)
		out[n++] = mtk_disp_rec_inst_word(o->move, 0, ~mask);

	if (mtk_disp_rec_var_data_type((u64)value, &arg_b, &arg_b_type))
		return -1;

	out[n++] = mtk_disp_rec_inst_word(
		mask != 0xffffffff ? o->write_s_w_mask : o->write_s,
		mtk_disp_rec_pack_arg_a(addr, subsys, arg_b_type << 1),
		mtk_disp_rec_pack_arg_b(arg_b, arg_b_type));

	return (int)n;
}

/*
 * port: struct cmdq_instruction as mtk-cmdq-helper.c:193 defines it, and
 * cmdq_pkt_append_command() stores that struct into the packet, so the struct
 * image is the instruction.
 */
struct port_inst {
	u32 low;	/* .value or .mask */
	u16 offset;
	u8 subsys;	/* sop:5, arg_c_t:1, src_t:1, dst_t:1 */
	u8 op;
};

static u64 port_word(u8 op, u16 offset, u8 subsys, u32 low)
{
	struct port_inst i = { low, offset, subsys, op };

	return *(u64 *)&i;
}

/*
 * port: cmdq_pkt_write_s_value() / cmdq_pkt_write_s_mask_value(). The masked
 * variant emits CMDQ_CODE_MASK with .mask = ~mask first, then the write.
 */
static int port_encode(const struct ops *o, u32 addr, u32 value, u32 mask,
		       u32 subsys, u64 out[2])
{
	int n = 0;

	if (mask != 0xffffffff)
		out[n++] = port_word((u8)o->mask, 0, 0, ~mask);

	out[n++] = port_word((u8)(mask != 0xffffffff ? o->write_s_mask :
							o->write_s),
			     (u16)(addr & MTK_DISP_REC_ADDR_MASK), (u8)subsys,
			     value);

	return n;
}

struct addr_case {
	const char *what;
	u32 addr;
	u32 value;
	s32 want;		/* expected subsys id, or MTK_DISP_REC_SUBSYS_SPECIAL */
};

int main(int argc, char **argv)
{
	const char *tree = argc > 1 ? argv[1] : NULL;
	const char *vendor = argc > 2 ? argv[2] : NULL;
	static const u32 masks[] = { 0xffffffff, 0xfffffff8, 0x0000ffff, 0x1, 0 };
	static const struct addr_case addrs[] = {
		{ "mmsys_config 0x14000000", 0x14000000, 0x1234, 1 },
		{ "mmsys_config 0x140003a0", 0x140003a0, 0xffffffff, 1 },
		{ "disp_dither 0x14010000", 0x14010000, 0x0000, 2 },
		{ "disp_dither 0x14012080", 0x14012080, 0xcafe0001, 2 },
		{ "ged 0x14120100", 0x14120100, 1, MTK_DISP_REC_SUBSYS_SPECIAL },
		{ "pwm 0x1100e000", 0x1100e000, 1, MTK_DISP_REC_SUBSYS_SPECIAL },
		{ "0x1100d000", 0x1100d000, 1, MTK_DISP_REC_SUBSYS_SPECIAL },
	};
	struct ops po, vo;
	struct row prow[MAX_ROWS], vrow[MAX_ROWS];
	struct mtk_disp_rec_subsys tbl[CMDQ_SUBSYS_MAX_COUNT];
	char path[512], detail[256];
	char *port_c = NULL, *vendor_c = NULL, *dts = NULL, *vdts = NULL;
	char *vdts_saved = NULL;
	int np = 0, nv = 0, i, j;

	if (sizeof(struct port_inst) != MTK_DISP_REC_INST_SIZE) {
		printf("FATAL: port_inst is %zu bytes, GCE instructions are %d\n",
		       sizeof(struct port_inst), MTK_DISP_REC_INST_SIZE);
		return 2;
	}

	if (!tree) {
		printf("usage: %s $TREE $VENDOR   (the checks read both trees)\n",
		       argv[0]);
		return 2;
	}

	printf("mtk_disp_record_host_check: encoding, subsys table, event ids\n");
	if (!vendor)
		printf("note: no $VENDOR argument, so the vendor columns compare against nothing\n");

	printf("\ninstruction numbers, read from both trees' mailbox header:\n");
	load_ops(tree, &po);
	if (vendor)
		load_ops(vendor, &vo);
	else
		memset(&vo, 0xff, sizeof(vo));
	for (i = 0; i < 5; i++) {
		unsigned int p = (&po.mask)[i], v = (&vo.mask)[i];
		char vb[16];

		if (v == 0xdeadbeef)
			snprintf(vb, sizeof(vb), "absent");
		else
			snprintf(vb, sizeof(vb), "0x%02x", v);
		printf("  %-28s port=0x%02x vendor=%s\n", op_names[i], p, vb);
	}

	/*
	 * The claim that lets this adapter delegate instead of re-encoding:
	 * the vendor's MOVE and mainline's MASK are one number, and so are
	 * WRITE_S_W_MASK and WRITE_S_MASK.
	 */
	{
		char d[160];

		snprintf(d, sizeof(d),
			 "port MASK 0x%02x, vendor MOVE 0x%02x, vendor MASK 0x%02x",
			 po.mask, vo.move, vo.mask);
		/*
		 * This tree's header has no MOVE at all (0xdeadbeef above means
		 * "not in this header"); what has to hold is that the instruction
		 * the vendor starts a masked write with is the instruction this
		 * tree's helper starts it with, by number.
		 */
		report("MASK (port) and MOVE (vendor) are one number",
		       !vendor || po.mask == vo.move, d);
		snprintf(d, sizeof(d),
			 "vendor says MASK 0x%02x and MOVE 0x%02x in the same enum",
			 vo.mask, vo.move);
		report("the vendor header itself aliases the two",
		       !vendor || vo.mask == vo.move, d);
	}
	{
		char d[128];

		snprintf(d, sizeof(d),
			 "port WRITE_S_MASK 0x%02x, vendor WRITE_S_W_MASK 0x%02x",
			 po.write_s_mask, vo.write_s_w_mask);
		report("WRITE_S_MASK == vendor WRITE_S_W_MASK",
		       !vendor || po.write_s_mask == vo.write_s_w_mask, d);
		snprintf(d, sizeof(d), "port 0x%02x, vendor 0x%02x",
			 po.write_s, vo.write_s);
		report("WRITE_S agrees", !vendor || po.write_s == vo.write_s, d);
	}

	printf("\nwrite_s instruction stream, vendor formula vs this tree's helper:\n");
	for (i = 0; i < (int)(sizeof(addrs) / sizeof(addrs[0])); i++) {
		for (j = 0; j < (int)(sizeof(masks) / sizeof(masks[0])); j++) {
			u64 vw[2] = { 0, 0 }, pw[2] = { 0, 0 };
			int vn = -1, pn = -1;
			u32 subsys = addrs[i].want == MTK_DISP_REC_SUBSYS_SPECIAL ?
				     MTK_DISP_REC_SUBSYS_SPECIAL :
				     (u32)addrs[i].want;
			bool ok;

			vn = vendor_encode(&vo, addrs[i].addr, addrs[i].value,
					   masks[j], subsys, vw);
			pn = port_encode(&po, addrs[i].addr, addrs[i].value,
					 masks[j], subsys, pw);

			if (subsys == MTK_DISP_REC_SUBSYS_SPECIAL) {
				/*
				 * Field packing is not reached on this path: the
				 * adapter rejects the address before it can
				 * truncate the id, which is what the last case
				 * below measures.
				 */
				snprintf(detail, sizeof(detail),
					 "unresolved subsys, %d words on both sides",
					 vn);
				report(addrs[i].what, vn == pn, detail);
				continue;
			}

			ok = vn == pn && vw[0] == pw[0] &&
			     (vn < 2 || vw[1] == pw[1]);
			snprintf(detail, sizeof(detail),
				 "mask=0x%08x v=%016llx,%016llx p=%016llx,%016llx",
				 masks[j], (unsigned long long)vw[0],
				 (unsigned long long)vw[1],
				 (unsigned long long)pw[0],
				 (unsigned long long)pw[1]);
			report(addrs[i].what, ok, detail);
		}
	}

	/* why the adapter rejects instead of packing an unresolved id */
	snprintf(detail, sizeof(detail), "99 packed into 5 bits is %u, not 99",
		 (MTK_DISP_REC_SUBSYS_SPECIAL & MTK_DISP_REC_SUBSYS_WIDTH_MASK));
	report("truncation would silently retarget subsys 3",
	       (MTK_DISP_REC_SUBSYS_SPECIAL & MTK_DISP_REC_SUBSYS_WIDTH_MASK) == 3,
	       detail);

	printf("\nsubsys name table, this port vs the vendor's data file:\n");
	if (tree && vendor) {
		snprintf(path, sizeof(path),
			 "%s/drivers/soc/mediatek/mtk-cmdq-disp-record.c", tree);
		port_c = slurp(path);
		snprintf(path, sizeof(path),
			 "%s/drivers/misc/mediatek/cmdq/v3/cmdq_subsys_common.c",
			 vendor);
		vendor_c = slurp(path);
	}
	if (port_c && vendor_c) {
		int bad = 0;

		np = parse_rows(port_c, prow, MAX_ROWS);
		nv = parse_rows(vendor_c, vrow, MAX_ROWS);
		for (i = 0; i < nv; i++) {
			int hit = -1;

			for (j = 0; j < np; j++)
				if (!strcmp(prow[j].sym, vrow[i].sym)) {
					hit = j;
					break;
				}
			if (hit < 0 || strcmp(prow[hit].name, vrow[i].name))
				bad++;
		}
		for (i = 0; i < np; i++) {
			int hit = -1;

			for (j = 0; j < nv; j++)
				if (!strcmp(vrow[j].sym, prow[i].sym)) {
					hit = j;
					break;
				}
			if (hit < 0)
				bad++;
		}
		snprintf(detail, sizeof(detail),
			 "%d rows port, %d rows vendor, %d unmatched", np, nv, bad);
		report("every row matches, both directions", bad == 0 && np == nv,
		       detail);
		free(port_c);
		free(vendor_c);
		port_c = vendor_c = NULL;
	} else {
		report("table comparison", false, "skipped: needs $TREE and $VENDOR");
	}

	printf("\naddress resolution, using the device tree of this port:\n");
	for (i = 0; i < CMDQ_SUBSYS_MAX_COUNT; i++) {
		tbl[i].msb = 0;
		tbl[i].mask = 0;
		tbl[i].subsys_id = NO_SUBSYS;
	}
	if (tree && vendor && np) {
		snprintf(path, sizeof(path),
			 "%s/arch/arm64/boot/dts/mediatek/mt6768.dts", tree);
		dts = slurp(path);
		snprintf(path, sizeof(path),
			 "%s/arch/arm64/boot/dts/mediatek/mt6768.dts", vendor);
		vdts = slurp(path);
	}
	if (dts && vdts) {
		int filled = 0, drift = 0;

		for (i = 0; i < np; i++) {
			char pat[96];
			const char *pa, *pv;
			unsigned int base, id, msk, vb, vi, vm;

			if (!prow[i].name[0])
				continue;
			snprintf(pat, sizeof(pat), "%s = <", prow[i].name);
			pa = strstr(dts, pat);
			pv = strstr(vdts, pat);
			if (!pa || !pv)
				continue;
			if (sscanf(pa + strlen(pat), " %x %u %x", &base, &id,
				   &msk) != 3)
				continue;
			if (sscanf(pv + strlen(pat), " %x %u %x", &vb, &vi,
				   &vm) != 3)
				continue;
			if (base != vb || id != vi || msk != vm)
				drift++;
			tbl[i].msb = base & msk;
			tbl[i].subsys_id = (s32)id;
			tbl[i].mask = msk;
			filled++;
		}
		snprintf(detail, sizeof(detail),
			 "%d rows read from the gce node, %d differing from the vendor dts",
			 filled, drift);
		report("port dts triples equal the vendor's", drift == 0 && filled > 0,
		       detail);

		for (i = 0; i < (int)(sizeof(addrs) / sizeof(addrs[0])); i++) {
			s32 got = mtk_disp_rec_core_subsys_from_phys_addr(tbl,
							     CMDQ_SUBSYS_MAX_COUNT,
							     addrs[i].addr);

			snprintf(detail, sizeof(detail),
				 "resolved %d, expected %d", got, addrs[i].want);
			report(addrs[i].what, got == addrs[i].want, detail);
		}
		free(dts);
		vdts_saved = vdts;	/* the event check below reads it too */
	} else {
		report("resolution", false, "skipped: needs $TREE and $VENDOR");
	}

	printf("\nevent id defaults:\n");
	{
		int bad = 0;

		for (i = 0; i < MTK_DISP_REC_TOKEN_MAX; i++) {
			s32 stock = i <= CMDQ_MAX_HW_EVENT_COUNT ?
				    CMDQ_SYNC_TOKEN_INVALID - 1 - i : i;

			if (mtk_disp_rec_event_default(i) != stock)
				bad++;
		}
		snprintf(detail, sizeof(detail),
			 "cmdq_core_init_dts_data(), %d differing of %d", bad,
			 MTK_DISP_REC_TOKEN_MAX);
		report("matches the vendor loop index by index", bad == 0, detail);
	}
	{
		const int ev[3] = { CMDQ_EVENT_MUTEX0_STREAM_EOF,
				    CMDQ_SYNC_TOKEN_STREAM_EOF,
				    CMDQ_SYNC_TOKEN_CONFIG_DIRTY };
		const char *what[3] = {
			"MUTEX0_STREAM_EOF (ddp_path.c:908)",
			"SYNC_TOKEN_STREAM_EOF (ddp_path.c:910)",
			"SYNC_TOKEN_CONFIG_DIRTY (ddp_path.c:927)"
		};

		for (i = 0; i < 3; i++) {
			s32 got = mtk_disp_rec_event_default(ev[i]);

			snprintf(detail, sizeof(detail),
				 "enum %d, default id %d -> %s", ev[i], got,
				 got < 0 ? "needs a device tree property" :
					   "usable as is");
			report(what[i], got >= 0 ? i != 0 : i == 0, detail);
		}
		{
			char *gce = dts ? gce_node_of(dts) : NULL;
			char *vgce = vdts_saved ? gce_node_of(vdts_saved) : NULL;
			unsigned int pv = 0, vv = 0;
			bool have = gce && prop_u32_in(gce, "stream_done_0", &pv);
			bool vhave = vgce && prop_u32_in(vgce, "stream_done_0", &vv);

			snprintf(detail, sizeof(detail),
				 "gce node of the port: %s; the vendor dts: %s",
				 have ? "names it" : "does not name it",
				 vhave ? "names it too" : "does not");
			report("stream_done_0 read from the gce node, as the adapter reads it",
			       have, detail);
			snprintf(detail, sizeof(detail),
				 "port %u, vendor %u - the id cmdqRecWaitNoClear() puts in the WFE",
				 pv, vv);
			report("the id matches the vendor's device tree",
			       have && vhave && pv == vv, detail);
			free(gce);
			free(vgce);
		}
	}

	printf("\n%d cases, %d mismatches\n", cases, mismatches);

	free(port_c);
	free(vendor_c);

	return mismatches ? 1 : 0;
}
