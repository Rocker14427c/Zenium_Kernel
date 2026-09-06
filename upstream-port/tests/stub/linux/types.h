/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Host-side stand-in for <linux/types.h>, the only reason the record harness can
 * compile a kernel header without the kernel build system. It defines the few
 * typedefs include/linux/soc/mediatek/mtk-cmdq-disp-record.h needs. The harness
 * passes -I upstream-port/tests/stub ahead of -I $TREE/include, so the real
 * kernel header is never reached.
 */
#ifndef _STUB_LINUX_TYPES_H
#define _STUB_LINUX_TYPES_H

#include <stdint.h>
#include <stddef.h>

typedef uint8_t		u8;
typedef uint16_t	u16;
typedef uint32_t	u32;
typedef uint64_t	u64;
typedef int8_t		s8;
typedef int16_t		s16;
typedef int32_t		s32;
typedef int64_t		s64;

#endif
