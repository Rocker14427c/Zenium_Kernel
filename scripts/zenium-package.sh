#!/usr/bin/env bash
#
# zenium-package.sh - wrap a *fresh* kernel build in the project's known-good
#                    AnyKernel3 scaffold and produce a release directory.
#
# Why this script exists: a freshly cloned osm0sis/AnyKernel3 has tuna-specific
# sample edits. The safe scaffold is the one already validated for this device
# family, which ships inside the previous release ZIP in this repo. This script
# extracts that scaffold, replaces ONLY the image + metadata, and produces a
# verified package. Nothing is uploaded or published.
#
# Usage:
#   scripts/zenium-package.sh --version V2.1.0 --name "KernelSU-Next+SUSFS+NoMount" \
#       [--scaffold release/ksunext-susfs-nomount-v2.0.0/<pkg>.zip] \
#       [--image out/arch/arm64/boot/Image.gz-dtb] \
#       [--branch <git-branch>] [--outdir release] [--notes <file.md>] [--yes]
#
# Defaults:
#   --image     out/arch/arm64/boot/Image.gz-dtb
#   --scaffold  newest release/*/*.zip that contains anykernel.sh
#   --outdir    release
#
# Output: <outdir>/<tag>/  containing the AnyKernel ZIP, SHA256SUMS,
#         RELEASE_NOTES.md, System.map and even_defconfig.config.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION=""; BASENAME=""; SCAFFOLD=""; IMAGE="out/arch/arm64/boot/Image.gz-dtb"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
OUTDIR="release"; NOTES=""; ASSUME_YES=0

die() { printf '\033[1;31m[-]\033[0m %s\n' "$*" >&2; exit 1; }
say() { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }
ask() { [ "$ASSUME_YES" -eq 1 ] && return 0; printf '\033[1;33m[?]\033[0m %s [y/N] ' "$*"; read -r a; case "$a" in y|Y|yes) return 0;; *) return 1;; esac; }

while [ $# -gt 0 ]; do
  case "$1" in
    --version)  VERSION="$2"; shift 2 ;;
    --name)     BASENAME="$2"; shift 2 ;;
    --scaffold) SCAFFOLD="$2"; shift 2 ;;
    --image)    IMAGE="$2"; shift 2 ;;
    --branch)   BRANCH="$2"; shift 2 ;;
    --outdir)   OUTDIR="$2"; shift 2 ;;
    --notes)    NOTES="$2"; shift 2 ;;
    --yes)      ASSUME_YES=1; shift ;;
    -h|--help)  sed -n '2,26p' "$0"; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
done
[ -n "$VERSION" ] || die "--version is required (e.g. V2.1.0)"
[ -n "$BASENAME" ] || die "--name is required (e.g. 'KSU-Next+SUSFS+NoMount')"

# ------------------------------------------------------------- preflight ----
[ -f "$IMAGE" ] || die "image not found: $IMAGE  (build first: scripts/build_susfs.sh)"
[ -s "$IMAGE" ] || die "image is empty: $IMAGE"
IMG_SHA="$(sha256sum "$IMAGE" | cut -d' ' -f1)"
IMG_SIZE="$(stat -c %s "$IMAGE")"
say "image: $IMAGE  ($IMG_SIZE bytes, sha256 $IMG_SHA)"

# refuse an image that does not carry this tree's identity
if command -v gzip >/dev/null; then
  BANNER="$(gzip -dc "$IMAGE" 2>/dev/null | strings | grep -aoE 'Linux version [^ ]+' | head -1 || true)"
  [ -n "$BANNER" ] && say "banner: $BANNER"
  case "$BANNER" in
    *Zenium*) : ;;
    "") printf '\033[1;33m[!]\033[0m could not read a version banner from the image\n' ;;
    *) printf '\033[1;33m[!]\033[0m banner does not contain "Zenium" - wrong/stock image?\n' ;;
  esac
fi

# pick a scaffold from a validated release if none was given
if [ -z "$SCAFFOLD" ]; then
  # newest in-repo package that actually contains an anykernel.sh
  # newest by the commit that last touched it (mtime is useless in a fresh clone)
  SCAFFOLD="$( for z in release/*/*.zip releases/*.zip; do
                 [ -f "$z" ] || continue
                 printf '%s %s\n' "$(git log -1 --format=%ct -- "$z" 2>/dev/null || echo 0)" "$z"
               done | sort -rn | while read -r _ z; do
                 unzip -l "$z" 2>/dev/null | grep -q ' anykernel.sh$' && { echo "$z"; break; }
               done )"
  [ -n "$SCAFFOLD" ] || die "no AnyKernel scaffold found in release/ or releases/; pass --scaffold <zip>"
fi
[ -f "$SCAFFOLD" ] || die "scaffold not found: $SCAFFOLD"
say "scaffold: $SCAFFOLD"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ------------------------------------------------------------- scaffold -----
unzip -q "$SCAFFOLD" -d "$WORK/ak3"
rm -f "$WORK/ak3/Image.gz-dtb" "$WORK/ak3/System.map" "$WORK/ak3"/*.config \
      "$WORK/ak3/SHA256SUMS" "$WORK/ak3/SHA512SUMS" "$WORK/ak3/RELEASE_NOTES.md"
command -v shellcheck >/dev/null && shellcheck -S error "$WORK/ak3/anykernel.sh" || true

AK="$WORK/ak3/anykernel.sh"
[ -f "$AK" ] || die "scaffold has no anykernel.sh"
# hard invariants for this device family
sed -i 's#^BLOCK=.*#BLOCK=/dev/block/by-name/boot;#'          "$AK"
sed -i 's#^IS_SLOT_DEVICE=.*#IS_SLOT_DEVICE=0;#'              "$AK"
sed -i 's#^do\.modules=.*#do.modules=0#'                      "$AK"
# refresh the banner string, keep the author line honest
NEW_STRING="Zenium-Kernel-RUI4-${VERSION}-${BASENAME} by Rocker14427c"
sed -i "s#^kernel\.string=.*#kernel.string=${NEW_STRING}#"     "$AK"
# ensure all six device names are present (idempotent)
for n in RMX3430 RMX3191 RMX3193 RMX3195 RMX3197 even; do
  grep -qE "device\.name[0-9]+=$n$" "$AK" || die "scaffold is missing device.name for $n"
done

cp "$IMAGE" "$WORK/ak3/Image.gz-dtb"
[ -f out/System.map ] && cp out/System.map "$WORK/ak3/System.map"
[ -f out/.config ]    && cp out/.config    "$WORK/ak3/even_defconfig.config"

# ----------------------------------------------------- release directory ----
TAG="$(echo "${VERSION}-${BASENAME}" | tr 'A-Z ' 'a-z-' | tr -cd 'a-z0-9._-')"
DEST="$OUTDIR/$TAG"
mkdir -p "$DEST"
ZIPNAME="Zenium-Kernel-RUI4-${VERSION}-${BASENAME}.zip"
ZIPNAME="$(echo "$ZIPNAME" | tr ' ' '_' | tr -cd 'A-Za-z0-9._+-')"
ZIP="$(cd "$DEST" && pwd)/$ZIPNAME"   # absolute; we zip from $WORK/ak3

# zip the CONTENTS of the scaffold (no extra parent directory)
( cd "$WORK/ak3" && zip -q -r -9 "$ZIP" . -x '.*' -x '*.git*' -x 'README.md' )
unzip -tq "$ZIP" >/dev/null || die "produced zip fails unzip -t"

# ------------------------------------------------------------- verify -------
Z_SHA="$(sha256sum "$ZIP" | cut -d' ' -f1)"
EMB_SHA="$(unzip -p "$ZIP" Image.gz-dtb | sha256sum | cut -d' ' -f1)"
[ "$Z_SHA" != "$EMB_SHA" ] || true
[ "$EMB_SHA" = "$IMG_SHA" ] || die "packaged image does not match the build output ($EMB_SHA != $IMG_SHA)"
echo "$Z_SHA  $(basename "$ZIP")" > "$DEST/SHA256SUMS"
[ -f out/System.map ] && cp out/System.map "$DEST/" || true
[ -f out/.config ]    && cp out/.config    "$DEST/even_defconfig.config" || true

# ------------------------------------------------------------- notes --------
if [ -n "$NOTES" ] && [ -f "$NOTES" ]; then
  cp "$NOTES" "$DEST/RELEASE_NOTES.md"
else
  {
    echo "# Zenium Kernel RUI4 ${VERSION} — ${BASENAME}"
    echo
    echo "Built from branch \`${BRANCH}\` at \`$(git rev-parse --short HEAD)\`."
    echo
    echo "- Image: \`$(basename "$IMAGE")\`, ${IMG_SIZE} bytes, sha256 \`${IMG_SHA}\`"
    [ -n "${BANNER:-}" ] && echo "- Banner: \`${BANNER}\`"
    echo "- SUSFS: \`$(sed -n 's/^#define SUSFS_VERSION "\(.*\)"/\1/p' include/linux/susfs.h | head -1)\`"
    echo "- NoMount: base \`$(sed -n 's/^#define NOMOUNT_BASE_VERSION "\(.*\)"/\1/p' fs/nomount/nomount.h | head -1)\`"
    echo "- Root backend: $(git config -f .gitmodules submodule.KernelSU.url) @ $(git ls-tree HEAD KernelSU | awk '{print substr($3,1,12)}')"
    echo
    echo "AnyKernel3 package: \`$(basename "$ZIP")\` (sha256 \`${Z_SHA}\`)."
    echo "Targets RMX3430, RMX3191, RMX3193, RMX3195, RMX3197 and \`even\`; \`boot\` partition only."
    echo
    echo "**Compile/link verified, not device tested.** Flashing is the user's responsibility."
  } > "$DEST/RELEASE_NOTES.md"
fi

say "produced: $ZIP"
say "sha256  : $Z_SHA"
say "release : $DEST/"
ask "Push branch $(git rev-parse --abbrev-ref HEAD) and publish a tag for $DEST?" || {
  echo "not pushed. To publish later:"
  echo "  git push origin $(git rev-parse --abbrev-ref HEAD)"
  echo "  git tag -a <tag> -m '<message>' && git push origin <tag>"
  exit 0
}
: