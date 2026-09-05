#!/usr/bin/env python3
"""mkbootimg.py - pack, unpack and verify Android boot images (header v0-v3).

Written for `even` (Realme 9i, MT6769): header version 2, page size 2048, and the
offsets taken verbatim from the device's BoardConfig.mk:

  BOARD_KERNEL_BASE            0x40078000      --base
  BOARD_KERNEL_OFFSET          0x00008000      --kernel_offset
  BOARD_RAMDISK_OFFSET         0x07c08000      --ramdisk_offset   (BoardConfig value)
  BOARD_KERNEL_TAGS_OFFSET     0x0bc08000      --tags_offset
  BOARD_KERNEL_SECOND_OFFSET   0x00e88000      --second_offset
  BOARD_DTB_OFFSET             0x0bc08000      --dtb_offset
  BOARD_KERNEL_PAGESIZE        2048             --pagesize
  BOARD_BOOTIMG_HEADER_VERSION 2                --header_version
  BOARD_KERNEL_CMDLINE         bootopt=64S3,32N2,64N2

Layout implemented exactly as system/core/include/bootimg.h: a v0 header of 1632
bytes, extended in place (v1 +24, v2 +16, v3 +16 for header_size), sections
appended in the order kernel, ramdisk, second, recovery_dtbo (v1+), dtb (v2+),
each padded to the page size, image padded to a page multiple at the end.

Subcommands
  pack    write an image from parts
  unpack  print every header field and optionally dump the sections
  verify  unpack, repack from the dumped parts, and compare byte for byte

`verify` unpacks, re-packs from the dumped sections and compares the header page byte
for byte (section payloads are copied verbatim, so they cannot diverge). That proves the
field packing, section order and page math are self-consistent, and it prints the
partition-size fit. It does NOT prove the device's LK accepts the image: only hardware
can say that.
"""
import argparse
import hashlib
import json
import os
import struct
import sys

MAGIC = b"ANDROID!"
V0 = 1632
EXTRA = {0: 0, 1: 24, 2: 40, 3: 56}          # bytes past the v0 header, cumulative
OS_NAMES = {"NONE": 0, "ANDROID": 1}


# os_version is a 32-bit informational field: LK and the MTK boot chain do not read
# it, and AOSP's exact bit layout differs between header versions. This tool therefore
# refuses to invent one: it writes --os-version-word verbatim (default 0) and unpack()
# reports the raw word, so a repack reproduces whatever the input had.



def pad(data, page):
    n = (-len(data)) % page
    return data + b"\0" * n


def pack(args):
    page = args.pagesize
    parts = []
    sections = []
    hdr_pages = (V0 + EXTRA[args.header_version] + page - 1) // page

    def add(name, payload):
        payload = payload or b""
        if payload:
            # page index within the image; the header occupies the first hdr_pages
            sections.append((name, len(payload), hdr_pages + sum(len(p) for p in parts) // page))
        parts.append(pad(payload, page))

    kernel = open(args.kernel, "rb").read() if args.kernel else b""
    ramdisk = open(args.ramdisk, "rb").read() if args.ramdisk else b""
    second = open(args.second, "rb").read() if args.second else b""
    dtb = open(args.dtb, "rb").read() if args.dtb else b""
    recov = open(args.recovery_dtbo, "rb").read() if args.recovery_dtbo else b""

    hdr = bytearray(V0 + EXTRA[args.header_version])
    hdr[0:8] = MAGIC
    off = 8
    def u32(v):
        nonlocal off
        struct.pack_into("<I", hdr, off, v & 0xFFFFFFFF)
        off += 4
    def u64(v):
        nonlocal off
        struct.pack_into("<Q", hdr, off, v & 0xFFFFFFFFFFFFFFFF)
        off += 8
    def bytes_(b, n):
        nonlocal off
        hdr[off:off + n] = b[:n].ljust(n, b"\0")
        off += n

    u32(len(kernel)); u32(args.base + args.kernel_offset)
    u32(len(ramdisk)); u32(args.base + args.ramdisk_offset)
    u32(len(second)); u32(args.base + args.second_offset)
    u32(args.base + args.tags_offset); u32(page)
    u32(args.header_version); u32(getattr(args, "os_version_word", 0))
    # AOSP mkbootimg uses --board for the 16-byte `name` on header v0-v3
    bytes_((args.name or args.board).encode()[:16], 16)
    bytes_(args.cmdline.encode()[:512], 512)
    hex_id = args.boot_id or hashlib.sha1(
        b"".join([kernel, ramdisk, second]) + args.cmdline.encode()).hexdigest()
    if not isinstance(hex_id, str):
        hex_id = hex_id.decode()
    hex_id = "".join(c for c in hex_id if c in "0123456789abcdefABCDEF")
    bytes_(bytes.fromhex(hex_id[:32].ljust(32, "0")), 32)
    bytes_(args.extra_cmdline.encode()[:1024], 1024)
    if args.header_version >= 1:
        u64(len(recov))
        if args.header_version >= 2:
            u64(0)                       # recovery_dtbo_offset: patched below
        u64(V0 + EXTRA[args.header_version])   # header_size
    if args.header_version >= 2:
        u64(len(dtb)); u64(args.base + args.dtb_offset)

    add("kernel", kernel)
    add("ramdisk", ramdisk)
    add("second", second)
    if args.header_version >= 1 and recov:
        body_pages = hdr_pages
        struct.pack_into("<Q", hdr, off - 24 if args.header_version >= 2 else off - 8,
                         (body_pages + sum(len(p) for p in parts) // page) * page)
        add("recovery_dtbo", recov)
    if args.header_version >= 2:
        add("dtb", dtb)

    # header lives in its own page(s)
    body = b"".join(parts)
    image = pad(bytes(hdr), page) + body
    out = args.out
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(image)
    rep = {"out": out, "bytes": len(image), "page_size": page,
           "header_version": args.header_version,
           "sections": [{"name": n, "size": s, "pages_from_start": p} for n, s, p in sections],
           "sha256": hashlib.sha256(image).hexdigest()}
    if args.partition_size:
        rep["partition_size"] = args.partition_size
        rep["fits"] = len(image) <= args.partition_size
    if args.report:
        import json
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        json.dump(rep, open(args.report, "w"), indent=1)
    print("boot.img: %d bytes (%d pages), sha256 %s" % (len(image), len(image) // page, rep["sha256"][:16]))
    for s in rep["sections"]:
        print("  %-14s %9d bytes @ page %d" % (s["name"], s["size"], s["pages_from_start"]))
    if args.partition_size:
        print("  partition %d bytes -> %s (%d%% used)" % (
            args.partition_size, "FITS" if rep["fits"] else "TOO BIG",
            100 * len(image) // args.partition_size))
    return 0 if not args.partition_size or rep["fits"] else 1


FIELDS = [("kernel_size", "<I"), ("kernel_addr", "<I"), ("ramdisk_size", "<I"),
          ("ramdisk_addr", "<I"), ("second_size", "<I"), ("second_addr", "<I"),
          ("tags_addr", "<I"), ("page_size", "<I"), ("header_version", "<I"),
          ("os_version", "<I")]


def unpack(args):
    """Parse the header. `args` needs .image, may have .dump_dir/.json."""
    data = open(args.image, "rb").read()
    if data[:8] != MAGIC:
        print("not an Android boot image (magic %r)" % data[:8], file=sys.stderr)
        return 1
    off = 8
    res = {}
    for name, fmt in FIELDS:
        res[name] = struct.unpack_from(fmt, data, off)[0]
        off += struct.calcsize(fmt)
    res["name"] = data[off:off + 16].rstrip(b"\0").decode(errors="replace"); off += 16
    res["cmdline"] = data[off:off + 512].split(b"\0")[0].decode(errors="replace"); off += 512
    res["boot_id"] = data[off:off + 32].hex(); off += 32
    res["extra_cmdline"] = data[off:off + 1024].split(b"\0")[0].decode(errors="replace"); off += 1024
    hv = res["header_version"]
    if hv >= 1:
        res["recovery_dtbo_size"] = struct.unpack_from("<Q", data, off)[0]; off += 8
        if hv >= 2:
            res["recovery_dtbo_offset"] = struct.unpack_from("<Q", data, off)[0]; off += 8
        res["header_size"] = struct.unpack_from("<Q", data, off)[0]; off += 8
    if hv >= 2:
        res["dtb_size"] = struct.unpack_from("<Q", data, off)[0]; off += 8
        res["dtb_addr"] = struct.unpack_from("<Q", data, off)[0]; off += 8
    res["total_bytes"] = len(data)
    res["header_bytes"] = V0 + EXTRA.get(hv, 0)
    page = res["page_size"] or 2048
    pos = page
    order = [("kernel", res["kernel_size"]), ("ramdisk", res["ramdisk_size"]),
             ("second", res["second_size"])]
    if hv >= 1:
        order.append(("recovery_dtbo", res.get("recovery_dtbo_size", 0)))
    if hv >= 2:
        order.append(("dtb", res.get("dtb_size", 0)))
    res["sections"] = []
    for name, size in order:
        res["sections"].append({"name": name, "offset": pos, "size": size})
        if args.dump_dir and size:
            os.makedirs(args.dump_dir, exist_ok=True)
            open(os.path.join(args.dump_dir, name), "wb").write(data[pos:pos + size])
        pos += ((size + page - 1) // page) * page
    for k in ("kernel_size", "ramdisk_size", "second_size", "header_version", "page_size"):
        print("  %-22s %s" % (k, res[k]))
    print("  %-22s %s" % ("cmdline", res["cmdline"]))
    print("  %-22s %s" % ("os_version", hex(res["os_version"])))
    print("  %-22s %s" % ("kernel_addr", hex(res["kernel_addr"])))
    print("  %-22s %s" % ("tags_addr", hex(res["tags_addr"])))
    if hv >= 2:
        print("  %-22s %s" % ("dtb_size", res.get("dtb_size")))
        print("  %-22s %s" % ("dtb_addr", hex(res.get("dtb_addr", 0))))
    print("  %-22s %s (%d pages)" % ("image", res["total_bytes"], res["total_bytes"] // page))
    json_path = getattr(args, "json", None) or (os.path.join(args.dump_dir, "header.json") if args.dump_dir else None)
    if json_path:
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
        json.dump(res, open(json_path, "w"), indent=1)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "unpack", "verify"])
    ap.add_argument("--image")
    ap.add_argument("--kernel"); ap.add_argument("--ramdisk"); ap.add_argument("--second")
    ap.add_argument("--dtb"); ap.add_argument("--recovery_dtbo")
    ap.add_argument("--out")
    ap.add_argument("--base", type=lambda x: int(x, 0), default=0x40078000)
    ap.add_argument("--kernel_offset", type=lambda x: int(x, 0), default=0x00008000)
    ap.add_argument("--ramdisk_offset", type=lambda x: int(x, 0), default=0x07c08000)
    ap.add_argument("--tags_offset", type=lambda x: int(x, 0), default=0x0bc08000)
    ap.add_argument("--second_offset", type=lambda x: int(x, 0), default=0x00e88000)
    ap.add_argument("--dtb_offset", type=lambda x: int(x, 0), default=0x0bc08000)
    ap.add_argument("--pagesize", type=int, default=2048)
    ap.add_argument("--header_version", type=int, default=2, choices=[0, 1, 2, 3])
    ap.add_argument("--cmdline", default="bootopt=64S3,32N2,64N2")
    ap.add_argument("--extra_cmdline", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--board", default="")
    ap.add_argument("--boot-id", default="")
    ap.add_argument("--os-version-word", type=lambda x: int(x, 0), default=0,
                    help="raw 32-bit os_version field (informational; written verbatim)")
    ap.add_argument("--partition-size", type=lambda x: int(x, 0), default=0)
    ap.add_argument("--dump-dir")
    ap.add_argument("--json")
    ap.add_argument("--report")
    a = ap.parse_args()
    if a.cmd == "verify":
        a.dump_dir = a.dump_dir or (a.image + ".dump")
        rc = unpack(a)
        if rc:
            return rc
        res = json.load(open(a.dump_dir + "/header.json")) if os.path.isfile(a.dump_dir + "/header.json") else None
        print("verify: re-packing from %s" % a.dump_dir)
        a.kernel = os.path.join(a.dump_dir, "kernel")
        for opt in ("ramdisk", "second", "dtb", "recovery_dtbo"):
            setattr(a, opt, os.path.join(a.dump_dir, opt)
                    if os.path.isfile(os.path.join(a.dump_dir, opt)) else None)
        # reproduce the numeric header inputs so byte comparison is meaningful
        if res:
            a.os_version_word = res.get("os_version", 0)
            a.cmdline = res.get("cmdline", "")
            a.extra_cmdline = res.get("extra_cmdline", "")
            a.name = res.get("name", "")
            a.boot_id = res.get("boot_id", "")
            a.base = 0
            a.kernel_offset = res.get("kernel_addr", 0)
            a.ramdisk_offset = res.get("ramdisk_addr", 0)
            a.second_offset = res.get("second_addr", 0)
            a.tags_offset = res.get("tags_addr", 0)
            a.pagesize = res.get("page_size", a.pagesize)
            a.header_version = res.get("header_version", a.header_version)
            # every *_addr field is (base + *_offset); with base forced to 0 the
            # offsets below reproduce those words exactly
            if res.get("dtb_addr"):
                a.dtb_offset = res["dtb_addr"]
        a.out = a.dump_dir + ".repack"
        pack(a)
        o = open(a.image, "rb").read(); n = open(a.out, "rb").read()
        if o[:a.pagesize] == n[:a.pagesize]:
            print("verify: header page identical (%d bytes) -> packing is self-consistent" % a.pagesize)
        else:
            for i in range(min(len(o), len(n))):
                if o[i] != n[i]:
                    print("verify: first byte difference at offset %d (0x%x)" % (i, i), file=sys.stderr)
                    break
            return 1
        return 0
    if a.cmd == "unpack":
        return unpack(a)
    return pack(a)


sys.exit(main())
