# Android 15 source reconciliation

These are source patches found outside the published component commits before
the Android 16 migration. `inventory.json` records the exact base revision and
the original patch hash. Apply only after reviewing the patch against that base.

SurfaceFlinger composition format and mediaextractor memfd changes are committed
directly in their component repositories on `lineage-22.1-mainline`.
The SwiftShader BGRA fallback patch remains here as a source input.

The other patches are an Android 15 archive, not defaults for Android 16:
renameat fallback and reduced dm-verity options target kernel 3.10; the DNS error
bypass and GPU-memory BPF disabling need review; the standalone netbpfload target
was a diagnostic build. Dialer/ThemePicker/SDK patches preserve build fixes and
branding. The USB catch-all is not carried to Android 16 automatically.

Modified binary blobs and tool replacements, untracked backups, Python caches,
and test helpers remain in the local source-state backup and protected Git
stashes. They are not published or silently applied to the new checkout.
