# KernelSU migration on the 4.19 device kernel

## Selected base

This branch replaces the BakaSU submodule with the `legacy` branch of
[KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next), pinned at
`e5f5ec998de88b9fc43c62cff8f7ae12d3f4800a`. The legacy Kconfig has an explicit
`CONFIG_KSU_MANUAL_HOOK` path suitable for kernels below 5.10 and retains the
credential and SELinux helpers used by this tree's SUSFS integration.

The current official KernelSU main branch was inspected first. Its kernel
Kconfig requires KPROBES and EXT4 and it no longer provides the legacy manual
hook option used by this kernel. A full target build could not be run in this
sandbox: the configuration step stops because `bison` is not installed, and no
AArch64 cross-compiler is available. Per the requested fallback, this branch
uses KernelSU-Next legacy rather than claiming the latest official source was
build-tested on this 4.19 tree.

## Integration details

- `CONFIG_KSU_MANUAL_HOOK=y` is selected; the existing device-tree call sites
  are adapted to the KernelSU-Next legacy function signatures.
- The existing SUSFS v2.4 4.19 core remains in `fs/susfs.c`. SUSFS commands are
  dispatched from the reboot syscall only when the KernelSU magic, SUSFS magic,
  and root effective UID match. The KSU-domain bridge uses KernelSU-Next's
  `is_ksu_domain()` and its `u:r:ksu:s0` SELinux context.
- The manager/`ksusfs` command client is not shipped in this kernel repository;
  use a userspace package that speaks the same SUSFS v2.4 reboot-command ABI.
  This bridge was checked against the kernel-side command IDs, but the external
  app/helper pairing has not been runtime-tested.
- SUSFS feature choices are declared in the kernel's `fs/Kconfig`. Existing
  device selections are retained; the unverified priority UID filter is not
  added or enabled.
- NoMount remains a separate `CONFIG_NOMOUNT` VFS subsystem and is not coupled
  to KernelSU. Its use of newer cleanup-based `rcu_guard()` was replaced with
  explicit RCU read-side sections for compatibility with this 4.19 tree.

## Validation status

`git diff --check` passes. Configuration/build validation is **not complete**:
`make O=/tmp/zenium-config ARCH=arm64 even_defconfig` fails before parsing the
configuration because `bison` is missing. No kernel image or device test was
run. The main commit therefore remains a buildability handoff for the user's
4.19 toolchain, not a claim of a tested kernel.
