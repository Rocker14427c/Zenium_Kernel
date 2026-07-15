/* SPDX-License-Identifier: GPL-2.0 */
/*
 * Copyright (c) 2020 MediaTek Inc.
 */

#ifndef __MMDVFS_CONFIG_MT6768_H__
#define __MMDVFS_CONFIG_MT6768_H__

#include "mmdvfs_config_util.h"

#define MT6768_MMDVFS_OPP_MAX 5

/* Part I QOS apply profiles */
struct mmdvfs_profile_mask qos_apply_profiles[] = {
	{"CAM_MON", MMDVFS_CAM_MON_SCEN,  MMDVFS_FINE_STEP_OPP0},
	{"CAM_PV",  SMI_BWC_SCEN_CAM_PV,  MMDVFS_FINE_STEP_OPP0},
	{"CAM_CP",  SMI_BWC_SCEN_CAM_CP,  MMDVFS_FINE_STEP_OPP0},
	{"VR",      SMI_BWC_SCEN_VR,      MMDVFS_FINE_STEP_OPP0},
	{"VSS",     SMI_BWC_SCEN_VSS,     MMDVFS_FINE_STEP_OPP0},
	{"ICFP",    SMI_BWC_SCEN_ICFP,    MMDVFS_FINE_STEP_OPP0},
	{"DEBUG",   SMI_BWC_SCEN_NORMAL,  MMDVFS_FINE_STEP_UNREQUEST},
};

/* Part II MMDVFS Scenario's Step Configuration */
#define MT6768_MMDVFS_OPP0_NUM 7
struct mmdvfs_profile mt6768_mmdvfs_opp0_profiles[MT6768_MMDVFS_OPP0_NUM] = {
	{"VR",      SMI_BWC_SCEN_VR,      {0, 0, 0}, {0, 0, 0}},
	{"VR_SLOW", SMI_BWC_SCEN_VR_SLOW, {0, 0, 0}, {0, 0, 0}},
	{"VSS",     SMI_BWC_SCEN_VSS,     {0, 0, 0}, {0, 0, 0}},
	{"ICFP",    SMI_BWC_SCEN_ICFP,    {0, 0, 0}, {0, 0, 0}},
	{"VENC",    SMI_BWC_SCEN_VENC,    {0, 0, 0}, {0, 0, 0}},
	{"CAM_PV",  SMI_BWC_SCEN_CAM_PV,  {0, 0, 0}, {0, 0, 0}},
	{"CAM_CP",  SMI_BWC_SCEN_CAM_CP,  {0, 0, 0}, {0, 0, 0}},
};

#define MT6768_MMDVFS_OPP1_NUM 0
struct mmdvfs_profile mt6768_mmdvfs_opp1_profiles[MT6768_MMDVFS_OPP1_NUM] = {};

#define MT6768_MMDVFS_OPP2_NUM 0
struct mmdvfs_profile mt6768_mmdvfs_opp2_profiles[MT6768_MMDVFS_OPP2_NUM] = {};

#define MT6768_MMDVFS_OPP3_NUM 0
struct mmdvfs_profile mt6768_mmdvfs_opp3_profiles[MT6768_MMDVFS_OPP3_NUM] = {};

#define MT6768_MMDVFS_OPP4_NUM 0
struct mmdvfs_profile mt6768_mmdvfs_opp4_profiles[MT6768_MMDVFS_OPP4_NUM] = {};

/* Part III Step to QOS step mapping */
struct mmdvfs_step_to_qos_step legacy_to_qos_step[MT6768_MMDVFS_OPP_MAX] = {
	{0, 0},
	{1, 0},
	{2, 1},
	{3, 1},
	{4, 2},
};

struct mmdvfs_step_profile mt6768_step_profile[MT6768_MMDVFS_OPP_MAX] = {
	{0, mt6768_mmdvfs_opp0_profiles, MT6768_MMDVFS_OPP0_NUM,
		{0, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, MMDVFS_CLK_MUX_NUM}},
	{1, mt6768_mmdvfs_opp1_profiles, MT6768_MMDVFS_OPP1_NUM,
		{0, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, MMDVFS_CLK_MUX_NUM}},
	{2, mt6768_mmdvfs_opp2_profiles, MT6768_MMDVFS_OPP2_NUM,
		{0, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, MMDVFS_CLK_MUX_NUM}},
	{3, mt6768_mmdvfs_opp3_profiles, MT6768_MMDVFS_OPP3_NUM,
		{0, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, MMDVFS_CLK_MUX_NUM}},
	{4, mt6768_mmdvfs_opp4_profiles, MT6768_MMDVFS_OPP4_NUM,
		{0, {0, 0, 0, 0, 0, 0, 0, 0, 0, 0}, MMDVFS_CLK_MUX_NUM}},
};

#endif /* __MMDVFS_CONFIG_MT6768_H__ */
