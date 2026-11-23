#!/usr/bin/env bash
#
# zenium-publish.sh - upload the artifacts of an already-created release
#                    directory as *GitHub release assets*, with retries.
#
# Background: the previous session gave up on release assets because uploads
# returned EOF from the sandbox. Large assets are uploaded with a resumable
# single-request curl (-T, --retry) here; if that keeps failing, fall back to
# committing the ZIP into release/<tag>/ (which is what the repo does today).
#
# Usage:
#   GITHUB_TOKEN=$(cat ~/.zenium/ghtok 2>/dev/null || echo "$GITHUB_TOKEN") \
#     scripts/zenium-publish.sh --tag v2.1.0-... --title "..." --dir release/<tag> [--draft]
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${REPO:-Rocker14427c/Zenium_Kernel}"
API="https://api.github.com/repos/$REPO"
TOKEN="${GITHUB_TOKEN:-}"
TAG=""; TITLE=""; DIR=""; DRAFT="false"; PRERELEASE="false"
die() { printf '\033[1;31m[-]\033[0m %s\n' "$*" >&2; exit 1; }
say() { printf '\033[1;32m[+]\033[0m %s\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --tag) T="$2"; shift 2;; --title) TITLE="$2"; shift 2;;
    --dir) DIR="$2"; shift 2;; --draft) DRAFT=true; shift;;
    --prerelease) PRERELEASE=true; shift;;
    --token) TOKEN="$2"; shift 2;;
    -h|--help) sed -n '2,20p' "$0"; exit 0;;
    *) die "unknown option $1";;
  esac
done
[ -n "$TOKEN" ] || die "no token: export GITHUB_TOKEN (read it from ~/.git-credentials rather than hard-coding it)"
[ -n "$TAG" ] || die "--tag is required"
[ -d "${DIR:-}" ] || die "--dir <release dir> is required"
[ -n "$TITLE" ] || TITLE="$TAG"

api() { curl -sS -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" "$@"; }

REL_ID="$(api "$API/releases/tags/$TAG" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("id",""))' 2>/dev/null || true)"
if [ -z "$REL_ID" ]; then
  say "creating release $TAG"
  REL_ID="$(api -X POST "$API/releases" -d "$(python3 - "$TAG" "$TITLE" "$DRAFT" "$PRERELEASE" <<'PY'
import json,sys
tag,title,draft,pre=sys.argv[1:5]
print(json.dumps({"tag_name":tag,"name":title,"draft":draft=="true","prerelease":pre=="true"}))
PY
)" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("id",""))')"
fi
[ -n "$REL_ID" ] || die "could not create/find release $TAG"

shopt -s nullglob
for f in "$DIR"/*; do
  name="$(basename "$f")"
  say "uploading $name ($(du -h "$f" | cut -f1))"
  url="$(api -X POST "$API/releases/$REL_ID/assets" \
          -H "Content-Type: application/octet-stream" \
          --data-binary "@$f" 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin).get("browser_download_url",""))' 2>/dev/null || true)"
  if [ -z "$url" ]; then
    # fall back to uploads.github.com with a retry loop
    url="$(curl -sS --retry 5 --retry-all-errors --retry-delay 3 \
            -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/octet-stream" \
            -T "$f" "https://uploads.github.com/repos/$REPO/releases/$REL_ID/assets?name=$name" \
            | python3 -c 'import sys,json;print(json.load(sys.stdin).get("browser_download_url",""))' 2>/dev/null || true)"
  fi
  [ -n "$url" ] && say "  -> $url" || printf '\033[1;33m[!]\033[0m upload of %s failed; commit it into release/ instead\n' "$name"
done
