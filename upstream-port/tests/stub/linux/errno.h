/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Host-side stand-in for <linux/errno.h>, for the record harness only. The
 * numbers are the kernel's, from include/uapi/asm-generic/errno-base.h and
 * include/uapi/asm-generic/errno.h of the same tree; the slice gate re-derives
 * each one from that header and fails if this file ever disagrees, so nothing
 * here is a hand-copied constant that can rot.
 */
#ifndef _STUB_LINUX_ERRNO_H
#define _STUB_LINUX_ERRNO_H

#define EPERM		1
#define ENOENT		2
#define EAGAIN		11
#define EFAULT		14
#define EBUSY		16
#define EINVAL		22
#define EOPNOTSUPP	95

#endif
