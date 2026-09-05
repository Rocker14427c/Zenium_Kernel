#!/bin/bash
# run-disp-m4u-host-test.sh - compile and execute the ported MT6768 display M4U
# client (video/mt6768/dispsys/ddp_m4u.c + video/mt6768/videox/disp_helper.c) on
# the host, against a recording M4U stub and the *real* m4u headers of the tree.
#
#   $1 = ported tree   (default /home/user/portwork/build)
#   $2 = vendor tree   (default /home/user/Zenium_Kernel) - used only for the
#                     client<->driver ABI probe (same probe compiled against the
#                     4.19 vendor m4u headers, to prove the port did not move
#                     the struct layout or the display port IDs)
#   $3 = optional json output path
set -uo pipefail

TREE=${1:-/home/user/portwork/build}
VENDOR=${2:-/home/user/Zenium_Kernel}
JSON=${3:-}
TESTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
T=$(mktemp -d /tmp/dispm4u.XXXXXX)
M4UDIR=$TREE/drivers/misc/mediatek/m4u
VDIR=$TREE/drivers/misc/mediatek/video/mt6768
SRC=("$TESTS/disp_m4u_host_test.c" "$VDIR/dispsys/ddp_m4u.c" "$VDIR/videox/disp_helper.c")

sh=$T/shim
mkdir -p "$sh/linux" "$sh/asm"
cp "$TESTS/disp_m4u_host_m4u.h" "$sh/m4u.h"
cat > "$sh/linux/types.h" <<'EOT'
#ifndef _SHIM_LINUX_TYPES_H
#define _SHIM_LINUX_TYPES_H
#include <stdint.h>
typedef uint8_t __u8; typedef int8_t __s8;
typedef uint16_t __u16; typedef int16_t __s16;
typedef uint32_t __u32; typedef int32_t __s32;
typedef uint64_t __u64; typedef int64_t __s64;
typedef unsigned long size_t;
#endif
EOT
cat > "$sh/linux/ioctl.h" <<'EOT'
#ifndef _SHIM_LINUX_IOCTL_H
#define _SHIM_LINUX_IOCTL_H
#define _IO(type, nr)          (((type) << 8) | (nr))
#define _IOR(type, nr, size)   (((type) << 8) | (nr))
#define _IOW(type, nr, size)   (((type) << 8) | (nr))
#define _IOWR(type, nr, size)  (((type) << 8) | (nr))
#define _IOC_NONE 0u
#endif
EOT
: > "$sh/linux/fs.h"; : > "$sh/linux/scatterlist.h"; : > "$sh/linux/mm.h"
: > "$sh/linux/io.h"; : > "$sh/linux/slab.h"; : > "$sh/asm/io.h"

# create empty shims for any other system header the closure asks for
{ grep -rhoE '#include <[a-z0-9_./-]+\.h>' "${SRC[@]}" "$VDIR/dispsys/"*.h "$VDIR/videox/disp_helper.h" \
  "$M4UDIR/2.0/m4u_v2.h" "$M4UDIR/2.0/m4u_v2_ext.h" "$M4UDIR/mt6768/m4u_port.h" 2>/dev/null; } \
| sed -E 's/#include <(.*)>/\1/' | sort -u | while read -r h; do
    case "$h" in linux/*|asm/*|soc/*|uapi/*|mach/*|mt-plat/*)
      [ -e "$sh/$h" ] || { mkdir -p "$sh/$(dirname "$h")"; : > "$sh/$h"; } ;;
    esac
  done

COMMON=(-std=gnu11 -g -O0 -Wall -Wno-unused-parameter -Wno-pointer-sign -Wno-format
        -Wno-unused-function -Wno-implicit-fallthrough
        -include "$TESTS/disp_m4u_host_shim.h" -DCONFIG_MTK_M4U=1
        -I"$sh" -I"$M4UDIR/mt6768" -I"$M4UDIR/2.0"
        -I"$VDIR/dispsys" -I"$VDIR/videox")

echo "== build (host) =="
if ! gcc "${COMMON[@]}" "${SRC[@]}" -o "$T/test" 2> "$T/build.log"; then
  echo "BUILD FAILED"; sed -n '1,40p' "$T/build.log"; exit 2
fi
grep -c warning "$T/build.log" | sed 's/^/warnings=: /'
gcc "${COMMON[@]}" "${SRC[@]}" -o "$T/test" 2>>"$T/build.log"

echo "== run =="
"$T/test" | tee "$T/out.txt"
rc=${PIPESTATUS[0]}

echo "== ABI probe: ported tree vs vendor tree =="
cat > "$T/abi.c" <<'EOT'
#include <stdio.h>
#include <stddef.h>
#include "m4u_port.h"
#include "m4u_v2_ext.h"
int main(void)
{
	printf("M4U_PORT_NR=%d M4U_PORT_DISP_OVL0=%d M4U_PORT_DISP_2L_OVL0_LARB0=%d\n",
	       M4U_PORT_NR, M4U_PORT_DISP_OVL0, M4U_PORT_DISP_2L_OVL0_LARB0);
	printf("M4U_PORT_DISP_RDMA0=%d M4U_PORT_DISP_WDMA0=%d\n",
	       M4U_PORT_DISP_RDMA0, M4U_PORT_DISP_WDMA0);
	printf("sizeof(m4u_port_config_struct)=%zu Virtuality@%zu domain@%zu Distance@%zu Direction@%zu\n",
	       sizeof(struct m4u_port_config_struct),
	       offsetof(struct m4u_port_config_struct, Virtuality),
	       offsetof(struct m4u_port_config_struct, domain),
	       offsetof(struct m4u_port_config_struct, Distance),
	       offsetof(struct m4u_port_config_struct, Direction));
	printf("M4U_PROT_READ=%d M4U_PROT_WRITE=%d M4U_FLAGS_SG_READY=%d M4U_FLAGS_FIX_MVA=%d\n",
	       M4U_PROT_READ, M4U_PROT_WRITE, M4U_FLAGS_SG_READY, M4U_FLAGS_FIX_MVA);
	return 0;
}
EOT
abi_tree() { # $1 = m4u/2.0 dir, $2 = m4u/<chip> dir, $3 = label
  if ! gcc -std=gnu11 -O0 -w -include "$TESTS/disp_m4u_host_shim.h" \
       -I"$sh" -I"$2" -I"$1" "$T/abi.c" -o "$T/abi_$3" 2>"$T/abi_$3.log"; then
    echo "abi probe ($3) build failed:"; sed -n '1,8p' "$T/abi_$3.log"; return 1
  fi
  "$T/abi_$3"
}
abi_tree "$M4UDIR/2.0" "$M4UDIR/mt6768" port > "$T/abi.port" || { echo "port abi probe failed"; printf "RESULT abi_port=build_failed\n"; }
abi_tree "$VENDOR/drivers/misc/mediatek/m4u/2.0" "$VENDOR/drivers/misc/mediatek/m4u/mt6768" vend \
  > "$T/abi.vendor" || { echo "vendor abi probe failed"; printf "RESULT abi_vendor=build_failed\n"; }
cat "$T/abi.port" | sed 's/^/ported  : /'
cat "$T/abi.vendor" | sed 's/^/vendor 4.19: /'
if [ -s "$T/abi.port" ] && [ -s "$T/abi.vendor" ]; then
  if diff -q "$T/abi.port" "$T/abi.vendor" >/dev/null; then
    echo "RESULT abi_identical=pass"
    echo "== ABI: ported m4u headers present the same client-facing ABI as the 4.19 vendor tree =="
  else
    echo "RESULT abi_identical=fail"; echo "== ABI DIFFERS =="; diff "$T/abi.port" "$T/abi.vendor"
  fi
fi

if [ -n "$JSON" ]; then
  python3 - "$T/out.txt" "$T/abi.port" "$T/abi.vendor" "$JSON" "$rc" <<'PY'
import json, sys, os
out, abip, abiv, dst, rc = sys.argv[1:6]
res = {}
for line in open(out):
    if line.startswith("RESULT "):
        k, _, v = line[7:].strip().partition("=")
        res[k] = v.strip()
def abi(p):
    d = {}
    if os.path.exists(p):
        for line in open(p):
            for tok in line.strip().split():
                if "=" in tok:
                    k, _, v = tok.partition("=")
                    if k and not k[0].isdigit():
                        d[k] = v
    return d
checks = int(res.get("checks", "0")); failed = int(res.get("failed", "0"))
doc = {
 "generated_for": "display M4U client (video/mt6768/dispsys/ddp_m4u.c, video/mt6768/videox/disp_helper.c) compiled from the ported tree and executed on the host",
 "verdict": "PASS" if failed == 0 and checks else "FAIL",
 "checks_total": checks,
 "checks_failed": failed,
 "exit_code": int(rc),
 "results": res,
 "abi_probe_ported": abi(abip),
 "abi_probe_vendor_419": abi(abiv),
 "abi_identical": res.get("abi_identical", "unknown") == "pass" or (abi(abip) == abi(abiv) and bool(abi(abip))),
 "scope_note": "host execution of the client's control flow and of the arguments it passes to M4U; the M4U side is a recording stub, so no MMIO, translation, SMI or boot behaviour is proven here",
}
open(dst, "w").write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
print("wrote %s" % dst)
PY
fi
rm -rf "$T"
exit $rc
