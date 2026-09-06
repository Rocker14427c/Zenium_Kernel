
/*
 * The read-to-data-register case, measured rather than assumed to be a delegation:
 * cmdqRecReadToDataRegister() (v3/cmdq_record.c:3936) is one line that calls
 * cmdq_op_read_to_data_register() (:1576), and that function's live branch on this board -
 * CMDQ_DATA_REG_PQ_COLOR is 0x04, below CMDQ_DATA_REG_JPEG_DST's 0x11 (cmdq_def.h:271/273,
 * landed) - is "op = CMDQ_CODE_READ_S, arg_a = reg + CMDQ_GPR_V3_OFFSET with the value type,
 * arg_b = hw_addr with the address type", handed to cmdq_append_command() and packed by
 * cmdq_append_rw_s_command() (:941-951). Mainline's cmdq_pkt_read_s() fills the same four
 * positions of the same 64-bit word: reg_dst into arg_a[15:0], the subsys index into
 * arg_a[20:16] (its sop is a 5-bit field, which is why the 0x1f here cannot overflow), the
 * destination-register tag into arg_a[23] (its dst_t), the address low half into arg_b[31:16]
 * (its src_reg), and 0x80 into arg_a[31:24]. tests/mtk_disp_record_host_check.c compares that
 * field by field for every address this tree can produce, which is what makes "the same word" a
 * measurement. The +CMDQ_GPR_V3_OFFSET is the one place the port has to do what the vendor did
 * inside its op rather than at the callsite, so it is added here and nowhere else.
 *
 * The vendor's other branch (dst_data_reg >= CMDQ_DATA_REG_JPEG_DST) is CMDQ_CODE_READ through
 * cmdq_append_wpr_command(), whose unresolvable-address case inserts a CMDQ_CODE_WFE on
 * CMDQ_SYNC_TOKEN_GPR_SET_4 and a CMDQ_CODE_MOVE into CMDQ_DATA_REG_DEBUG. 5.15's
 * include/linux/mailbox/mtk-cmdq-mailbox.h has no CMDQ_CODE_READ enumerator at all (measured: the
 * harness looks for it and reports it absent), this port carries no GPR detour (KNOWN-ISSUES.md
 * 14), and struct cmdq_instruction plus cmdq_pkt_append_command() are private to
 * drivers/soc/mediatek/mtk-cmdq-helper.c, so there is nothing to build such a word with without
 * editing mainline code. It is therefore refused, loudly, and no landed callsite reaches it.
 */
s32 cmdqRecReadToDataRegister(struct cmdqRecStruct *handle, u32 hw_addr,
	enum cmdq_gpr_reg dst_data_reg)
{
	struct cmdq_pkt *pkt;
	u32 subsys;
	s32 ret;

	if ((u32)dst_data_reg >= (u32)CMDQ_DATA_REG_JPEG_DST) {
		pr_err_once("mtk-cmdq-disp-record: data register %u is at or above CMDQ_DATA_REG_JPEG_DST, which needs the wpr read path this port does not carry\n",
			    dst_data_reg);
		return -EOPNOTSUPP;
	}

	pkt = mtk_disp_rec_pkt(handle);
	if (IS_ERR(pkt))
		return PTR_ERR(pkt);

	ret = mtk_disp_rec_resolve_subsys(hw_addr, &subsys);
	if (ret < 0)
		return ret;

	return cmdq_pkt_read_s(pkt, (u8)subsys, hw_addr & MTK_DISP_REC_ADDR_MASK,
			       (u16)(dst_data_reg + CMDQ_GPR_V3_OFFSET));
}
EXPORT_SYMBOL(cmdqRecReadToDataRegister);
