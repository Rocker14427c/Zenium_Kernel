#!/usr/bin/env python3
"""rec0092c.py - one-word fix in the MANIFEST header: the "carried forward, not re-run" note still named
the 0091 round as the one that touched no older file; 0092 is the current round and touches only
ddp_mmp.c + its Makefile, so the sentence is true of it too and should say so."""
import os, sys
p = "/home/user/Zenium_Kernel/upstream-port/patch-series/MANIFEST.txt"
s = open(p).read()
old = "#           forward and not re-run, because 0091 touches no file that any of them contains):"
new = "#           forward and not re-run, because 0092 touches no file that any of them contains):"
if s.count(old) != 1:
    sys.exit("anchor not unique: %d" % s.count(old))
open(p, "w").write(s.replace(old, new, 1))
print("edited patch-series/MANIFEST.txt")
