/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Fake <m4u.h> for the host test, shadowing
 * drivers/misc/mediatek/m4u/mt6768/m4u.h (which pulls linux/mm.h, pgtable,
 * iommu and procfs and cannot build on a host).
 *
 * Nothing here is re-declared by hand: it includes the real
 * 2.0/m4u_v2.h of the ported tree, which in turn includes the real
 * m4u_port.h (port IDs, M4U_PORT_NR) and m4u_v2_ext.h
 * (struct m4u_port_config_struct, M4U_PROT_*, M4U_FLAGS_*,
 * m4u_fault_callback_t).  So the display client under test is compiled against
 * exactly the declarations the M4U driver exports, and the only fakes are the
 * five implementations in disp_m4u_host_test.c.  Prototype agreement is thus
 * guaranteed by construction, and independently by the kernel build.
 */
#ifndef _FAKE_M4U_H_FOR_HOST_TEST
#define _FAKE_M4U_H_FOR_HOST_TEST

struct page;
struct vm_area_struct;
struct file;
struct seq_file;
struct device;
struct iommu_domain;

#include "m4u_v2.h"

#endif /* _FAKE_M4U_H_FOR_HOST_TEST */
