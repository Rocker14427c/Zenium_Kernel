// SPDX-License-Identifier: GPL-2.0
/*
 * cmdq_words_host_check.c - verify, on the host, that the CMDQ instruction words produced by
 * v5.15.220's mtk-cmdq-helper.c encoders are bit-identical to the words the 4.19.325 Realme "even"
 * vendor encoder produces for the same operation.
 *
 * Why this exists: patch 0083 justified cmdq_pkt_wait_no_clear() as "a wrapper that emits the
 * identical 64-bit instruction". That is a claim about hardware-visible bytes, so it must be
 * checked by computing the bytes, not by reading two files and nodding. Both trees build the word
 * out of a file-private struct:
 *
 *   vendor 4.19.325  drivers/soc/mediatek/mtk-cmdq-helper.c:73   (bitfields, packed by
 *                    cmdq_pkt_instr_encoder() at :643 through a 9-argument
 *                    cmdq_pkt_append_command())
 *   mainline v5.15.220 drivers/soc/mediatek/mtk-cmdq-helper.c:22  (unions, appended by
 *                    cmdq_pkt_append_command(pkt, inst))
 *
 * so the only honest equivalence test is: run each tree's own builder over the same inputs and
 * compare the resulting u64. This file transcribes both structs, both encoders and the WFE-family
 * builders verbatim; the constants come from the two copies of
 * include/linux/mailbox/mtk-cmdq-mailbox.h (vendor :41-44, v5.15 :19-31) which define the four
 * CMDQ_WFE_* bits identically, and from the vendor opcode enum.
 *
 * The third block computes - but does not port - the sleep/TPR encodings, so the semantics that
 * stage 3 would need are on record as measured numbers. They are unreachable on this board: every
 * cmdq_pkt_sleep() occurrence in the display path is inside a slash-star comment (ddp_dsi.c:7099) and
 * every cmdq_pkt_sleep_by_poll() callsite and the vendor definition itself sit under
 * #ifdef CONFIG_MTK_MT6382_BDG (even_defconfig: # CONFIG_MTK_MT6382_BDG is not set), and the
 * GPR bookkeeping helper cmdq_pkt_poll_gpr_check() is wholly inside
 * #if IS_ENABLED(CONFIG_MACH_MT6885).
 *
 * Build and run (host gcc, no kernel headers):
 *   gcc -O1 -Wall -Wextra -o /tmp/cmdqwords upstream-port/tests/cmdq_words_host_check.c
 *   /tmp/cmdqwords
 * Exit status 0 = every compared pair identical.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef int32_t  s32;

#define BIT(n) (1UL << (n))

/* --- constants shared by both trees (measured in each copy of the header) --- */
#define CMDQ_INST_SIZE     8
#define CMDQ_CODE_MASK     0x02
#define CMDQ_CODE_WRITE    0x04
#define CMDQ_CODE_POLL     0x08
#define CMDQ_CODE_JUMP     0x10
#define CMDQ_CODE_WFE      0x20
#define CMDQ_CODE_EOC      0x40
#define CMDQ_CODE_READ_S   0x80
#define CMDQ_CODE_WRITE_S  0x90
#define CMDQ_CODE_WRITE_S_W_MASK 0x91
/* vendor-only (v5.15.220's enum has no entry for these) */
#define CMDQ_CODE_LOGIC          0xa0
#define CMDQ_CODE_JUMP_C_ABS     0xb0
#define CMDQ_CODE_JUMP_C_REL     0xb1
#define CMDQ_CODE_SET_TOKEN      0x21
#define CMDQ_CODE_WAIT_NO_CLEAR  0x22
#define CMDQ_CODE_CLEAR_TOKEN    0x23

#define CMDQ_WFE_UPDATE        BIT(31)
#define CMDQ_WFE_UPDATE_VALUE  BIT(16)
#define CMDQ_WFE_WAIT          BIT(15)
#define CMDQ_WFE_WAIT_VALUE    0x1

/* the two trees name their "default WFE" option differently and that is the whole point */
#define V_CMDQ_WFE_OPTION  (CMDQ_WFE_UPDATE | CMDQ_WFE_WAIT | CMDQ_WFE_WAIT_VALUE) /* vendor */
#define M_CMDQ_WFE_OPTION  (CMDQ_WFE_WAIT | CMDQ_WFE_WAIT_VALUE)                   /* v5.15  */

#define V_CMDQ_EVENT_MAX   0x3FF   /* vendor include/linux/soc/mediatek/mtk-cmdq.h:25 */
#define M_CMDQ_MAX_EVENT   0x3ff   /* v5.15  include/linux/mailbox/mtk-cmdq-mailbox.h */

#define CMDQ_IMMEDIATE_VALUE 0
#define CMDQ_REG_TYPE        1

/* vendor sleep-family constants, transcribed (not used to port anything) */
#define CMDQ_SPR_FOR_TEMP    0
#define CMDQ_THR_SPR_IDX0    0
#define CMDQ_THR_SPR_IDX1    1
#define CMDQ_THR_SPR_IDX2    2
#define CMDQ_THR_SPR_IDX3    3
#define CMDQ_TPR_ID          56
#define CMDQ_GPR_CNT_ID      32
#define CMDQ_CPR_TPR_MASK    0x8000
#define CMDQ_CPR_SLP_GPR_MAX 0x8003
#define CMDQ_EVENT_GPR_TIMER 994
#define CMDQ_TPR_MASK        0xD0
#define CMDQ_TPR_TIMEOUT_EN  0xDC
#define CMDQ_US_TO_TICK(t)   ((t) * 26)

enum CMDQ_LOGIC_ENUM {
	CMDQ_LOGIC_ASSIGN = 0, CMDQ_LOGIC_ADD = 1, CMDQ_LOGIC_SUBTRACT = 2,
	CMDQ_LOGIC_MULTIPLY = 3, CMDQ_LOGIC_XOR = 8, CMDQ_LOGIC_NOT = 9,
	CMDQ_LOGIC_OR = 10, CMDQ_LOGIC_AND = 11,
	CMDQ_LOGIC_LEFT_SHIFT = 12, CMDQ_LOGIC_RIGHT_SHIFT = 13
};
enum CMDQ_CONDITION_ENUM {
	CMDQ_CONDITION_ERROR = -1, CMDQ_EQUAL = 0, CMDQ_NOT_EQUAL = 1,
	CMDQ_GREATER_THAN_AND_EQUAL = 2, CMDQ_LESS_THAN_AND_EQUAL = 3,
	CMDQ_GREATER_THAN = 4, CMDQ_LESS_THAN = 5, CMDQ_CONDITION_MAX
};

/* ---------------- vendor 4.19.325 layout and encoder, verbatim ---------------- */
struct v_instruction {
	u16 arg_c:16;
	u16 arg_b:16;
	u16 arg_a:16;
	u8  s_op:5;
	u8  arg_c_type:1;
	u8  arg_b_type:1;
	u8  arg_a_type:1;
	u8  op:8;
};

static void v_instr_encoder(u64 *out, u16 arg_c, u16 arg_b, u16 arg_a, u8 s_op,
			    u8 arg_c_type, u8 arg_b_type, u8 arg_a_type, u8 op)
{
	struct v_instruction inst;

	memset(&inst, 0, sizeof(inst));
	inst.op = op;
	inst.arg_a_type = arg_a_type;
	inst.arg_b_type = arg_b_type;
	inst.arg_c_type = arg_c_type;
	inst.s_op = s_op;
	inst.arg_a = arg_a;
	inst.arg_b = arg_b;
	inst.arg_c = arg_c;
	*out = *(u64 *)&inst;
}

#define V_GENMASK(hi, lo) (((1UL << ((hi) - (lo) + 1)) - 1) << (lo))
#define V_GET_ARG_B(arg)  (((arg) & V_GENMASK(31, 16)) >> 16)
#define V_GET_ARG_C(arg)  ((arg) & V_GENMASK(15, 0))

static int v_pkt_wfe(u64 *w, u16 event)              /* wait and clear */
{
	u32 arg_b;

	if (event >= V_CMDQ_EVENT_MAX)
		return -1;
	arg_b = CMDQ_WFE_UPDATE | CMDQ_WFE_WAIT | CMDQ_WFE_WAIT_VALUE;
	v_instr_encoder(w, V_GET_ARG_C(arg_b), V_GET_ARG_B(arg_b), event,
			0, 0, 0, 0, CMDQ_CODE_WFE);
	return 0;
}

static int v_pkt_wait_no_clear(u64 *w, u16 event)
{
	u32 arg_b;

	if (event >= V_CMDQ_EVENT_MAX)
		return -1;
	arg_b = CMDQ_WFE_WAIT | CMDQ_WFE_WAIT_VALUE;
	v_instr_encoder(w, V_GET_ARG_C(arg_b), V_GET_ARG_B(arg_b), event,
			0, 0, 0, 0, CMDQ_CODE_WFE);
	return 0;
}

static int v_pkt_acquire_event(u64 *w, u16 event)
{
	u32 arg_b;

	if (event >= V_CMDQ_EVENT_MAX)
		return -1;
	arg_b = CMDQ_WFE_UPDATE | CMDQ_WFE_UPDATE_VALUE | CMDQ_WFE_WAIT;
	v_instr_encoder(w, V_GET_ARG_C(arg_b), V_GET_ARG_B(arg_b), event,
			0, 0, 0, 0, CMDQ_CODE_WFE);
	return 0;
}

static int v_pkt_clear_event(u64 *w, u16 event)
{
	if (event >= V_CMDQ_EVENT_MAX)
		return -1;
	v_instr_encoder(w, V_GET_ARG_C(CMDQ_WFE_UPDATE), V_GET_ARG_B(CMDQ_WFE_UPDATE),
			event, 0, 0, 0, 0, CMDQ_CODE_WFE);
	return 0;
}

/* cmdq_pkt_logic_command() / _assign_command() / _cond_jump_abs() as the vendor builds them */
struct v_operand {
	bool reg;
	union {
		u16 idx;
		u16 value;
	};
};
#define V_OPERAND_IDX_VALUE(o) ((o)->reg ? (o)->idx : (o)->value)
#define V_OPERAND_TYPE(o)      ((o)->reg ? CMDQ_REG_TYPE : CMDQ_IMMEDIATE_VALUE)

static void v_pkt_logic_command(u64 *w, u8 s_op, u16 result_reg_idx,
				struct v_operand *left, struct v_operand *right)
{
	v_instr_encoder(w, V_OPERAND_IDX_VALUE(right), V_OPERAND_IDX_VALUE(left),
			result_reg_idx, s_op, V_OPERAND_TYPE(right),
			V_OPERAND_TYPE(left), CMDQ_REG_TYPE, CMDQ_CODE_LOGIC);
}

static void v_pkt_assign_command(u64 *w, u16 reg_idx, u32 value)
{
	v_instr_encoder(w, V_GET_ARG_C(value), V_GET_ARG_B(value), reg_idx,
			CMDQ_LOGIC_ASSIGN, CMDQ_IMMEDIATE_VALUE, CMDQ_IMMEDIATE_VALUE,
			CMDQ_REG_TYPE, CMDQ_CODE_LOGIC);
}

static void v_pkt_cond_jump_abs(u64 *w, u16 addr_reg_idx, struct v_operand *left,
				struct v_operand *right, u8 cond)
{
	v_instr_encoder(w, V_OPERAND_IDX_VALUE(right), V_OPERAND_IDX_VALUE(left),
			addr_reg_idx, cond, V_OPERAND_TYPE(right), V_OPERAND_TYPE(left),
			CMDQ_REG_TYPE, CMDQ_CODE_JUMP_C_ABS);
}

/* ---------------- v5.15.220 layout and encoders, verbatim ---------------- */
struct m_instruction {
	union {
		u32 value;
		u32 mask;
		struct {
			u16 arg_c;
			u16 src_reg;
		};
	};
	union {
		u16 offset;
		u16 event;
		u16 reg_dst;
	};
	union {
		u8 subsys;
		struct {
			u8 sop:5;
			u8 arg_c_t:1;
			u8 src_t:1;
			u8 dst_t:1;
		};
	};
	u8 op;
};

static int m_pkt_wfe(u64 *w, u16 event, bool clear)
{
	struct m_instruction inst;

	memset(&inst, 0, sizeof(inst));
	if (event >= M_CMDQ_MAX_EVENT)
		return -1;
	inst.op = CMDQ_CODE_WFE;
	inst.value = M_CMDQ_WFE_OPTION | (clear ? CMDQ_WFE_UPDATE : 0);
	inst.event = event;
	*w = *(u64 *)&inst;
	return 0;
}

static int m_pkt_clear_event(u64 *w, u16 event)
{
	struct m_instruction inst;

	memset(&inst, 0, sizeof(inst));
	if (event >= M_CMDQ_MAX_EVENT)
		return -1;
	inst.op = CMDQ_CODE_WFE;
	inst.value = CMDQ_WFE_UPDATE;
	inst.event = event;
	*w = *(u64 *)&inst;
	return 0;
}

/* patch 0083's wrapper, exactly as shipped */
static int m_pkt_wait_no_clear(u64 *w, u16 event)
{
	return m_pkt_wfe(w, event, false);
}

/* ---------------------------- test driver ---------------------------- */
static int fails, checks;

static void eq(const char *name, u64 v, u64 m, int rv, int rm)
{
	checks++;
	if (rv != rm) {
		printf("  %-44s MISMATCH return codes vendor=%d mainline=%d\n", name, rv, rm);
		fails++;
		return;
	}
	if (rv) {
		printf("  %-44s both reject (rc=%d) - bounds agree\n", name, rv);
		return;
	}
	if (v != m) {
		printf("  %-44s MISMATCH vendor=%016llx mainline=%016llx\n", name,
		       (unsigned long long)v, (unsigned long long)m);
		fails++;
		return;
	}
	printf("  %-44s identical word=%016llx\n", name, (unsigned long long)v);
}

int main(void)
{
	static const u16 events[] = { 0, 1, 2, 96, 97, 98, 99, 100, 511, 993, 994, 995,
				      1022, 1023, 1024, 2047 };
	u64 v = 0, m = 0;
	size_t i;

	printf("CMDQ instruction-word equivalence: vendor 4.19.325 vs v5.15.220 (+0083)\n");
	printf("  sizeof(vendor struct cmdq_instruction)   = %zu\n", sizeof(struct v_instruction));
	printf("  sizeof(mainline struct cmdq_instruction) = %zu\n", sizeof(struct m_instruction));
	if (sizeof(struct v_instruction) != CMDQ_INST_SIZE ||
	    sizeof(struct m_instruction) != CMDQ_INST_SIZE) {
		printf("FATAL: a layout is not 8 bytes; the transcription is wrong\n");
		return 2;
	}

	printf("\n[1] cmdq_pkt_wait_no_clear(ev) [vendor]  vs  cmdq_pkt_wfe(ev, false) [0083 wrapper]\n");
	for (i = 0; i < sizeof(events) / sizeof(*events); i++) {
		char nm[96];
		int rv = v_pkt_wait_no_clear(&v, events[i]);
		int rm = m_pkt_wait_no_clear(&m, events[i]);

		snprintf(nm, sizeof(nm), "wait_no_clear ev=0x%03x", events[i]);
		eq(nm, v, m, rv, rm);
	}

	printf("\n[2] cmdq_pkt_wfe(ev) [vendor, wait+clear] vs cmdq_pkt_wfe(ev, true) [mainline]\n");
	for (i = 0; i < sizeof(events) / sizeof(*events); i++) {
		char nm[96];
		int rv = v_pkt_wfe(&v, events[i]);
		int rm = m_pkt_wfe(&m, events[i], true);

		snprintf(nm, sizeof(nm), "wfe_clear ev=0x%03x", events[i]);
		eq(nm, v, m, rv, rm);
	}

	printf("\n[3] cmdq_pkt_clear_event(ev): vendor vs mainline (display path calls this 4x)\n");
	for (i = 0; i < sizeof(events) / sizeof(*events); i++) {
		char nm[96];
		int rv = v_pkt_clear_event(&v, events[i]);
		int rm = m_pkt_clear_event(&m, events[i]);

		snprintf(nm, sizeof(nm), "clear_event ev=0x%03x", events[i]);
		eq(nm, v, m, rv, rm);
	}

	printf("\n[4] vendor-only encodings, computed for the record - NOT ported for this board\n");
	{
		struct v_operand l = { .reg = true }, r = { .reg = false };
		u32 tick;

		v_pkt_logic_command(&v, CMDQ_LOGIC_SUBTRACT, CMDQ_GPR_CNT_ID + 3, &l, &r);
		printf("  logic SUBTRACT GPR%d := TPR - 1              word=%016llx\n",
	       CMDQ_GPR_CNT_ID + 3, (unsigned long long)v);
		l.idx = CMDQ_TPR_ID; r.value = 1;
		v_pkt_logic_command(&v, CMDQ_LOGIC_SUBTRACT, CMDQ_GPR_CNT_ID + 3, &l, &r);
		printf("  logic SUBTRACT GPR%d := TPR[56] - 1           word=%016llx\n",
	       CMDQ_GPR_CNT_ID + 3, (unsigned long long)v);
		l.idx = CMDQ_CPR_TPR_MASK; r.value = 1u << 3;
		v_pkt_logic_command(&v, CMDQ_LOGIC_OR, CMDQ_CPR_TPR_MASK, &l, &r);
		printf("  logic OR CPR_TPR_MASK |= 1<<reg_gpr           word=%016llx\n",
	       (unsigned long long)v);
		tick = CMDQ_US_TO_TICK(28);
		l.idx = CMDQ_TPR_ID; r.value = (u16)tick;
		v_pkt_logic_command(&v, CMDQ_LOGIC_ADD, CMDQ_GPR_CNT_ID + 3, &l, &r);
		printf("  logic ADD GPR%d := TPR + %u (28us)      word=%016llx\n",
	       CMDQ_GPR_CNT_ID + 3, tick, (unsigned long long)v);
		v_pkt_assign_command(&v, CMDQ_SPR_FOR_TEMP, 0);
		printf("  assign SPR0 := 0                                word=%016llx\n",
	       (unsigned long long)v);
		v_pkt_assign_command(&v, CMDQ_CPR_SLP_GPR_MAX, 0xFFFFFF00);
		printf("  assign CPR_SLP_GPR_MAX := 0xFFFFFF00            word=%016llx\n",
	       (unsigned long long)v);
		v_pkt_acquire_event(&v, 994);
		printf("  acquire_event ev=994 (no mainline equivalent)   word=%016llx\n",
	       (unsigned long long)v);
		l.reg = true; l.idx = CMDQ_TPR_ID;
		r.reg = true; r.idx = CMDQ_GPR_CNT_ID + 3;
		v_pkt_cond_jump_abs(&v, CMDQ_SPR_FOR_TEMP, &l, &r, CMDQ_GREATER_THAN_AND_EQUAL);
		printf("  cond jump abs TPR>=GPR%d -> SPR0            word=%016llx\n",
	       CMDQ_GPR_CNT_ID + 3, (unsigned long long)v);
	}

	printf("\n%d comparisons, %d mismatches\n", checks, fails);
	printf("scope note: block [4] documents words for a path this board never compiles\n");
	printf("  (ddp_dsi.c:7099 is inside a /* */ comment; every sleep_by_poll callsite and the\n");
	printf("   vendor definition sit under #ifdef CONFIG_MTK_MT6382_BDG, unset on even; and\n");
	printf("   cmdq_pkt_poll_gpr_check() is wholly inside #if IS_ENABLED(CONFIG_MACH_MT6885))\n");
	return fails ? 1 : 0;
}
