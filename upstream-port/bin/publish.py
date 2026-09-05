#!/usr/bin/env python3
"""publish.py - turn the top commit(s) of the landing tree into the next published patch(es).

This flow used to be an ad-hoc script in /home/user/portwork/ (publish84.py) and a sandbox reset took
it, so the last round's renumbering had to be redone by hand under time pressure. Everything here is
checked rather than assumed:

  * the patch count is asserted before and after - an empty glob or a silently skipped file is how a
    stale "applied=81" claim once got into a report here;
  * the /NN denominator is rewritten in the Subject of every existing patch AND of the cover letter,
    and the run aborts if any file still carries the old one. This has to be fold-tolerant: `git
    format-patch` wraps long subjects at punctuation too, so the stored 0084 reads
        Subject: [PATCH 84
         /84] video/mt6768: land the CMDQ-free dispsys core ...
    i.e. the fold can land INSIDE the bracket group. A `[PATCH NNNN/NN]` literal therefore does not
    match it, and a tool that "found no subject" in one file of 84 would publish a set where one patch
    still says /84 - which is exactly the kind of thing that reads fine in a summary and breaks an
    `am -s` changelog. Folded subjects are unfolded (a legal header continuation removed), so the
    output is uniform instead of half-renumbered;
  * numerator width follows git's own rule (padded to the denominator's width: /84 -> "01".."84",
    cover "00"), while the file names keep this repo's 4-digit prefix;
  * finally the installed set is verified to reproduce: `git am` of 0001-NNNN in a scratch worktree
    must yield the landing tree's HEAD^{tree} exactly, and the 0001-(NNNN-1) prefix must still yield
    the previously published tree (that is what "do not regress the landed base" means in this repo).
    Without that step, publishing a *description* of a build rather than the build is one typo away.

Usage:
  publish.py --tree /home/user/portwork/series --expect-tree <HEAD^{tree} of that tree> \
             [--prev-tree <HEAD^{tree} of 0001..NN-1>] [--manifest-block FILE] [--dry-run]
"""
import argparse
import glob
import os
import re
import subprocess
import sys

# tolerant of a fold (newline + indent) anywhere inside the bracket group
SUBJ_RE = re.compile(r"\[PATCH\s+(\d{1,4})\s*/\s*(\d{1,3})\s*\]", re.S)


def sh(cmd, cwd=None, allow_fail=False):
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str), capture_output=True, text=True)
    if p.returncode != 0 and not allow_fail:
        sys.exit("command failed (%s)\n%s\n%s" % (cmd, p.stdout[-1500:], p.stderr[-1500:]))
    return p


def numbered(series):
    return sorted(p for p in glob.glob(os.path.join(series, "[0-9][0-9][0-9][0-9]-*.eml"))
                  if "cover" not in os.path.basename(p))


def unfold_subject(txt):
    """Join a folded `Subject:` header onto one line. Only that header is touched, and the result is
    still a plain valid header because the fold is removed rather than re-inserted."""
    out, changed = [], 0
    for line in txt.split("\n"):
        if out and out[-1].startswith("Subject:") and line[:1] in (" ", "\t"):
            out[-1] = out[-1].rstrip() + " " + line.strip()
            changed = 1
        elif changed and line[:1] in (" ", "\t") and out and not out[-1].startswith("Subject:"):
            out.append(line)          # a different folded header (From:, References:) - leave alone
        else:
            if changed and line[:1] not in (" ", "\t"):
                changed = 0
            out.append(line)
            if line.startswith("Subject:"):
                changed = 1
    return "\n".join(out)


def reproduce(series, tree, ref, upto, expect, label):
    """`git am` patches 0001..`upto` in a scratch worktree and compare the tree with `expect`."""
    wt = os.path.join(os.path.dirname(tree), ".publish-check")
    sh(["rm", "-rf", wt], tree)
    sh(["git", "-C", ref, "worktree", "add", "--detach", wt, "v5.15.220"], tree)
    sh(["git", "config", "user.name", "Zenium Port"], wt)
    sh(["git", "config", "user.email", "port@zenium.invalid"], wt)
    lst = " ".join(sorted(p for p in glob.glob(os.path.join(series, "[0-9]*.eml"))
                          if "cover" not in p and int(re.match(r".*/(\d{4})-", p).group(1)) <= upto))
    if not lst:
        sys.exit("empty am list for %s - that is how a false 'applied' claim happens" % label)
    n = len(lst.split())
    p = subprocess.run("git am -q %s" % lst, cwd=wt, shell=True, capture_output=True, text=True)
    got = sh(["git", "rev-parse", "HEAD^{tree}"], wt, allow_fail=True).stdout.strip()
    dirty = len([x for x in sh(["git", "status", "--porcelain"], wt).stdout.split("\n") if x.strip()])
    print("  %-22s am rc=%d files=%d dirty=%d tree=%s" % (label, p.returncode, n, dirty, got))
    ok = (p.returncode == 0 and n == upto and got == expect and not dirty)
    sh(["rm", "-rf", wt], tree)
    sh(["git", "-C", ref, "worktree", "prune"], tree)
    if not ok:
        sys.exit("REPRODUCTION FAILED for %s (want %s); published set does not rebuild the tree"
                 % (label, expect))
    print("  %s: VERIFIED - the .eml set rebuilds tree %s" % (label, got))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True, help="landing tree (git worktree holding the published series)")
    ap.add_argument("--repo", default="/home/user/Zenium_Kernel")
    ap.add_argument("--series", default=None, help="patch-series dir; default <repo>/upstream-port/patch-series")
    ap.add_argument("--expect-tree", required=True, help="HEAD^{tree} the full published set must reproduce")
    ap.add_argument("--prev-tree", default=None, help="HEAD^{tree} the 0001..N-1 prefix must still reproduce")
    ap.add_argument("--count", type=int, default=1, help="how many top commits to publish (usually 1)")
    ap.add_argument("--manifest-block", default=None, help="file with the MANIFEST entry for the new patch")
    ap.add_argument("--ref", default="/home/user/portwork/ref/linux", help="base repo holding v5.15.220")
    ap.add_argument("--no-verify", action="store_true", help="skip the git am reproduction (never for real runs)")
    ap.add_argument("--verify-only", action="store_true", help="install nothing; re-run the count and "
                    "reproduction checks on the series as it stands on disk. Used after amending a "
                    "commit message, where the tree is unchanged by construction but the .eml is not.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    series = a.series or os.path.join(a.repo, "upstream-port/patch-series")

    head_tree = sh(["git", "rev-parse", "HEAD^{tree}"], tree).stdout.strip()
    if head_tree != a.expect_tree:
        sys.exit("landing tree HEAD^{tree} = %s, expected %s - refusing to publish" % (head_tree, a.expect_tree))
    if sh(["git", "status", "--porcelain"], tree).stdout.strip():
        sys.exit("landing tree is dirty; commit the slice first")

    patches = numbered(series)
    if not patches:
        sys.exit("no patches found in %s" % series)
    old_n = int(re.match(r"(\d{4})-", os.path.basename(patches[-1])).group(1))
    if old_n != len(patches):
        sys.exit("latest patch is %04d but there are %d numbered files - the series has a hole"
                 % (old_n, len(patches)))
    new_n = old_n + a.count
    den_w = len(str(new_n))
    print("published now: %d patches (latest %04d); adding %d -> denominator becomes %d"
          % (len(patches), old_n, a.count, new_n))

    if a.verify_only:
        print("--verify-only: not installing or renumbering anything")
        reproduce(series, tree, a.ref, old_n, head_tree, "full series 0001-%04d" % old_n)
        if a.prev_tree:
            reproduce(series, tree, a.ref, old_n - a.count, a.prev_tree,
                      "prefix 0001-%04d" % (old_n - a.count))
        return

    # 1. the new .eml file(s). --subject-prefix carries the numbering, because `git format-patch -1`
    #    otherwise emits a bare "[PATCH]" and a 1-of-N set never gets numbered at all.
    for i in range(a.count):
        idx = old_n + i + 1
        rev = "HEAD~%d" % (a.count - 1 - i)
        p = sh(["git", "format-patch", "-1", "--stdout",
                "--subject-prefix=PATCH %0*d/%d" % (den_w, idx, new_n), rev], tree)
        out = unfold_subject(p.stdout)
        if not SUBJ_RE.search(out[:out.index("\n\n")]):
            sys.exit("generated patch %04d has no recognizable [PATCH n/N] subject" % idx)
        slug = re.search(r"(?m)^Subject: \[PATCH[^\]]*\][ \t]*(.*)$", out).group(1)
        slug = re.sub(r"[^A-Za-z0-9._+-]+", "-", slug).strip("-")[:54]
        name = "%04d-%s.eml" % (idx, slug)
        dst = os.path.join(series, name)
        if os.path.exists(dst):
            sys.exit("refusing to overwrite existing %s" % dst)
        if not a.dry_run:
            open(dst, "w").write(out)
        print("installed: %s (%d B)" % (name, len(out)))

    # 2. bump the denominator on every pre-existing patch and on the cover letter
    def bump(path):
        txt = unfold_subject(open(path).read())
        head, sep, rest = txt.partition("\n\n")
        hits = [m for m in SUBJ_RE.finditer(head) if m.group(2) != str(new_n)]
        if not hits:
            return 0
        new_head = SUBJ_RE.sub(lambda m: "[PATCH %0*d/%d]" % (den_w, int(m.group(1)), new_n), head)
        if not a.dry_run:
            open(path, "w").write(new_head + sep + rest)
        return len(hits)

    bumped = sum(bump(p) for p in patches)
    cover = os.path.join(series, "0000-cover-letter.eml")
    bumped += bump(cover) if os.path.exists(cover) else 0
    stale = []
    checked = numbered(series)
    if os.path.exists(cover) and cover not in checked:
        checked.append(cover)
    if a.dry_run:   # nothing was written, so every file is still "stale" by construction - report, do not fail
        print("(dry run: %d of %d files would have their denominator rewritten)" % (bumped, len(checked)))
        stale = []
        checked = []
    for p in checked:
        t = open(p).read()
        head = t[:t.index("\n\n")]
        if re.search(r"(?m)^Subject:.*\[PATCH\s+\d{1,4}\s*$", head):
            sys.exit("%s: subject still folded inside the bracket group - inspect it" % p)
        for m in SUBJ_RE.finditer(head):
            if m.group(2) != str(new_n):
                stale.append("%s: /%s" % (os.path.basename(p), m.group(2)))
    if stale:
        sys.exit("denominator still stale in %d place(s): %s" % (len(stale), stale[:6]))
    print("subjects normalized in %d place(s); every patch now carries /%d" % (bumped, new_n))

    # 3. MANIFEST block for the new patch(es)
    if a.manifest_block:
        mf = os.path.join(series, "MANIFEST.txt")
        block = open(a.manifest_block).read().rstrip("\n")
        t = open(mf).read()
        if not a.dry_run:
            open(mf, "w").write(t.rstrip("\n") + "\n" + block + "\n")
        print("MANIFEST: appended a %d-line block" % len(block.split("\n")))

    # 4. count + reproduction
    got_n = len(numbered(series))
    if got_n != new_n:
        sys.exit("series dir holds %d numbered patches, expected %d" % (got_n, new_n))
    print("series count check: %d numbered patches == %d  OK" % (got_n, new_n))
    if a.no_verify or a.dry_run:
        print("(reproduction not run)")
        return

    reproduce(series, tree, a.ref, new_n, head_tree, "full series 0001-%04d" % new_n)
    if a.prev_tree:
        reproduce(series, tree, a.ref, new_n - a.count, a.prev_tree,
                  "prefix 0001-%04d" % (new_n - a.count))


if __name__ == "__main__":
    main()
