# Stock GPIO-state paths and the atag handover: resolved (no code, no build)

Closes the open items of `panel-path-analysis.md` section 6 and corrects one mechanism description
from the previous round. All statements are grep/sed output from the 4.19 vendor tree in this
repository, with `file:line`. Nothing was compiled or linked - the 5.15 build environment is still
absent (`display-bringup-plan.md` section 5) - and no device tree was edited.

## 1. `disp_dts_gpio_init_repo()`: a macro over a 109-line pinctrl shim

The definition "not located" last round because it is not a function. In
`drivers/misc/mediatek/video/mt6768/videox/disp_dts_gpio.h:71-75`:

    #ifdef CONFIG_MTK_LEGACY
    #define disp_dts_gpio_init_repo(x)  (0)
    #else
    #define disp_dts_gpio_init_repo(x)  (disp_dts_gpio_init(x))
    #endif

and the whole implementation is `video/mt6768/videox/disp_dts_gpio.c`, **109 lines**, built for this
board (`videox/Makefile:40  obj-y += disp_dts_gpio.o`). It has three functions:

- `long disp_dts_gpio_init(struct platform_device *pdev)` - `pctrl = devm_pinctrl_get(&pdev->dev)`;
  on error logs `Cannot find disp pinctrl!` and returns `PTR_ERR`; else caches the handle in
  `static struct pinctrl *this_pctrl` and returns 0.
- `static long _set_state(const char *name)` - NULL handle gives `this pctrl is null` and -1;
  otherwise `pr_info("GPIO STATE state=%s")`, `pinctrl_lookup_state(this_pctrl, name)`,
  `pinctrl_select_state(this_pctrl, pState)`, with `lookup state '%s' failed` on miss.
- `long disp_dts_gpio_select_state(enum DTS_GPIO_STATE s)` - bounds-checks against
  `DTS_GPIO_STATE_MAX` (`GPIO STATE is invalid,state=%d`) and calls `_set_state(this_state_name[s])`.

Both bodies collapse to `return 0` under `CONFIG_FPGA_EARLY_PORTING` - which sets
`dts_gpio_state == 0` and so *selects* the pinctrl branch of every consumer while making that branch
a no-op: under early porting the reset line is not driven by the kernel at all.

### The state names are the binding

`this_state_name[DTS_GPIO_STATE_MAX]` (`disp_dts_gpio.c:17-48`), verbatim in enum order:
`mode_te_gpio`, `mode_te_te`, `mode_te1_te`, `lcm_rst_out0_gpio`, `lcm_rst_out1_gpio`,
`lcm1_rst_out0_gpio`, `lcm1_rst_out1_gpio`, then under `#ifdef OPLUS_BUG_STABILITY`:
`lcd_bias_enp0_gpio`, `lcd_bias_enp1_gpio`, `lcd_bias_enn0_gpio`, `lcd_bias_enn1_gpio`
(plus `6382_rst_out0/1_gpio` under `CONFIG_MTK_MT6382_BDG`, with `lcd_vddio18_en0/1_gpio` commented
out); the non-OPLUS arm is shorter, and then unconditionally `tp_rst_out1_gpio`, `tp_rst_out0_gpio`,
`6382_rst_out1_gpio`, `6382_rst_out0_gpio`. `OPLUS_BUG_STABILITY` is defined globally by this tree's
top-level `Makefile:657-660` (`KBUILD_CFLAGS`, `KBUILD_CPPFLAGS`, `CFLAGS_KERNEL`), so the OPLUS arms
are the live ones and the four `lcd_bias_*` states exist on this board.

So the "DTS GPIO" mechanism is **ordinary mainline pinctrl states, requested on the mtkfb platform
device, identified by those names** - and the touch reset pin rides the same table as panel reset
(`tp_rst_out*`), which is worth knowing for the client stage.

## 2. Reset, TE and bias, as actually wired

| signal | path | evidence |
|---|---|---|
| LCM reset (dsi0) | `lcm_set_reset_pin()`: `if (dts_gpio_state != 0) DSI_OUTREG32(NULL, DISP_REG_CONFIG_MMSYS_LCM_RST_B, value)` **else** `disp_dts_gpio_select_state(DTS_GPIO_STATE_LCM_RST_OUT1/OUT0)` | `dispsys/ddp_dsi.c:4959-4969` |
| LCM1 reset (dsi1) | same shape with `LCM1_RST_OUT1/OUT0` | `ddp_dsi.c:5005-5007` |
| LCD bias VSP/VSN | `lcm_bias_vsp()` / `lcm_bias_vsn()` -> `select_state(LCD_BIAS_ENP1/ENP0/ENN1/ENN0)` after `pr_err("[lcm]set vsp value is %d")`; reached by the panels through `SET_LCM_VSP_PIN`/`SET_LCM_VSN_PIN` | `ddp_dsi.c:4971-4990`; panels `:43-44` |
| LCD VDDIO18 | `lcm_vddio18_enable()` logs `[lcm]no need set vddio18`; body is `#if 0` | `ddp_dsi.c`, just after the bias helpers |
| gate IC (AVDD/AVEE) | `display_bias_setting(0x14)` -> I2C writes to SM5109/OCP2130 (previous round) | `lcm/lcm_i2c.c:219-280` |
| TE | **not a driver hook on dsi0**: the DSI0 util set gets `utils->set_te_pin = NULL`, `lcm1_set_te_pin` is assigned only for DSI1; dsi0 TE is `static int dsi0_te_enable = 1` + `PanelMaster_get_TE_status()`, with the `mode_te_*` states muxing the pin | `ddp_dsi.c:196`, `:5218-5250`, `:7499-7506`, `:5010` |
| PWM states | `ddp_pwm.c:402,412` select `DTS_GPIO_STATE_DISP_PWM_TRANSPARENT` / `..._GPIO_LOW`; unused by these three panels, which dim over DCS 0x51 | `video/common/pwm10/ddp_pwm.c` |

The only per-board data the kernel needs for reset/bias is therefore a pinctrl node exposing those
named states - and the board DT does not provide them:
`mtkfb: mtkfb@0 { compatible = "mediatek,mtkfb"; };` (`mt6768.dts:3120-3122`), and the `dispsys`
node immediately after it (`:3125`) has none either. So which branch runs on a real device is decided
by what `devm_pinctrl_get()` returns for a device with no `pinctrl-names` in 4.19 - answerable on
5.15 from `drivers/pinctrl/core.c`, and observable on a device from
`GPIO STATE state=...` / `Cannot find disp pinctrl!` / `lookup state ... failed` in the log. Both
branches are recorded here so the port copies a decision rather than a guess. What the port must not
do is substitute `gpio_set_value()`-style numbers: nothing on this board supplies them.

## 3. The `atag,videolfb-*` producer: where LK ends and the kernel begins

- **LK is not in this repository** - top level has no `lk`, `lk2`, `project` or `bootable` directory
  (listed) - so the writer cannot be read from here. The kernel side is a pure consumer:
  `grep -rn "of_add_property\|__of_add_property\|of_update_property" drivers/misc/mediatek/video/`
  returns nothing.
- Kernel-side reads, in `video/mt6768/videox/mtkfb.c`: `parse_tag_videolfb()` takes
  `of_find_node_by_path("/chosen")`, falls back to `/chosen@0`, is single-shot behind
  `is_videofb_parse_done`, then tries `__parse_tag_videolfb()` and `__parse_tag_videolfb_extra()`.
  Nine names appear in that file: `atag,videolfb` and `atag,ext_videolfb` (the legacy whole-blob
  form) plus `atag,videolfb-fb_base_h`, `-fb_base_l`, `-islcmfound`, `-islcm_inited`, `-fps`,
  `-vramSize`, `-lcmname`. `_parse_tag_videolfb(void)` is the exported entry
  (`drivers/misc/mediatek/video/include/mtkfb.h:410`, next to `extern unsigned int islcmconnected`
  and `vramsize`). `__parse_tag_videolfb_extra()` defaults `is_lcm_inited = 1` when
  `atag,videolfb-islcm_inited` is absent, and returns -1 when `-fb_base_h`, `-fb_base_l`,
  `-islcmfound` or `-fps` is absent.
- The shape LK must produce is documented in-tree by MTK's own BSP fallback,
  `arch/arm64/boot/dts/mediatek/k65v1_64_bsp.dts:20-27`:
  `atag,videolfb-fb_base_h = <0x0>; ... -fb_base_l = <0x5e605000>; -islcmfound = <1>;
  -islcm_inited = <0>; -fps = <6000>; -vramSize = <0x017bb000>;` and
  `atag,videolfb-lcmname = "nt35695B_fhd_dsi_cmd_auo_rt5081_drv";` - u32 cells plus a
  NUL-terminated string carrying the `_drv` suffix, and note the DT spells it `-islcm_inited` while
  the kernel variable is `is_lcm_inited`.
- This board's packaged DTB has 0 `atag,videolfb` properties (measured last round), consistent with
  LK injecting them into the DT it hands over at boot: on a device they exist only in the runtime
  DT, never in the flashed image's DTB.

## 4. What the kernel does with the name (correction to last round)

`mtkfb_find_lcm_driver()` is not a selector. Measured, it is:

    mtkfb_find_lcm_driver(void)
    {
        _parse_tag_videolfb();
        DISPMSG("%s, %s\n", __func__, mtkfb_lcm_name);
        return mtkfb_lcm_name;
    }

It parses idempotently and hands the string to `primary_display_init(plcm_name, lcd_fps,
is_lcm_inited)`. In `videox/disp_lcm.c` (~:1060-1130, inside `#ifdef OPLUS_BUG_STABILITY`) the name
is then *classified*:

    tddic_temp = strstr(plcm_name, "ili7807s");
    if (tddic_temp != NULL) {
        temp = tddic_temp + strlen("ili7807s");
        if (!strncmp(temp, "_xxx_fhd_dsi_vdo_dphy_lcm_drv", strlen(...)))     lcm_panel_temp = "CSOT_ILI";
        else if (!strncmp(temp, "_jdi_fhd_dsi_vdo_dphy_lcm_drv", strlen(...))) lcm_panel_temp = "JDI_ILI";
        else                                                                  lcm_panel_temp = "TEMP_DEFAULT_ILI";
        setLcmPanel_ID(1);
    } else { strstr "hx83112a" -> "_lead_hdp_dsi_vdo_lcm_drv" -> "LEAD_HX" / "NULL_HX";
             strstr "ili9881tfh" -> "_txd_..." / "_lide_..." -> "TXD_ILI_TF" / "LIDE_ILI_TF", setLcmPanel_ID(0);
             strstr "nt36525b"  -> "_hlt_hdp_dsi_vdo_lcm_drv" -> "HELITAI_NT" else "ELSE_NT", setLcmPanel_ID(1);
             strstr "Simulator" ... }

plus `strncpy(Lcm_name1, plcm_name, strlen(plcm_name)+1)` when `is_lcm_inited == 1`, logged as
`" lcm name IS %s"`. Two port consequences:
(i) the suffix ladder is part of the mechanism - dropping it silently disables the per-supplier
variant switch (`setLcmPanel_ID`) that the panel drivers and the touch side can consume;
(ii) `load_lcm_resources_from_DT()` (`disp_lcm.c:990`, which would call `lcm_drv->parse_dts`) is
inside the `#if defined(MTK_LCM_DEVICE_TREE_SUPPORT)` starting at `:186`, so it is not compiled here
- the third independent confirmation that no DT-driven LCM resource loading is live on this board,
and hence no DT-based panel-selection model is warranted.

## 5. One open item, with the command that closes it

`struct tag_videolfb` - the blob layout behind `atag,videolfb`/`atag,ext_videolfb`, needed only if
the port reads the legacy blob instead of per-field properties - is in neither
`include/video/mtkfb.h` nor `drivers/misc/mediatek/video/include/mtkfb.h` in this tree (both
`lcmname` greps empty), yet `video/common/mtkfb_dummy.c:522-525` uses `videolfb_tag->lcmname`, so it
is reachable from that translation unit. Close it with
`grep -rn "lcmname" --include='*.h' . | grep -i "char\|\["`. Remember that `mtkfb_dummy.c` is not
built when `CONFIG_MTK_FB=y` (`common/Makefile:103`), so the blob form is only worth keeping if LK
on some variant still supplies it.

Nothing here is a claim about 5.15 behaviour or about a booted device.
