# Platform decisions

## Upload: not supported in v1

`pio run -t upload` fails with a clear message: the HEX is the deliverable
and flashing is left to the user's own programmer (pk2cmd, ipecmd, a
bootloader). The alternatives were considered and rejected for v1:

- **pk2cmd / ipecmd wrappers.** Both are Microchip tools, and the platform's
  reason to exist is a build path with no Microchip downloads (design doc 31
  D-5). Wrapping them would make the platform depend on the very downloads
  it exists to avoid.
- **A bootloader protocol.** Real work with no hardware to validate against
  in this repo, and no consumer asking for it yet.

The decision is recorded here so it is not relitigated per PR. When a
programmer integration lands, it belongs in a `tool-*` package (PIO-2
shape), not in the platform core.

## Size reporting: deferred to epic-cc CC-6

PlatformIO's `size` target expects a toolchain size report. epic-cc's own
report (CC-6, `epic-cc#74`) landed on master but is not in the released
toolchain (v0.0.3), so `pio run -t size` states that the report is not
available rather than deriving a number from the HEX. The HEX is the whole
flash image, so usage cannot be computed from it; the compiler's report is
the source of truth and the target flips to it when a toolchain with CC-6
is released.

## Manifest schema: verified against PlatformIO 6.1.19

The `[VERIFY]` in the PIO-1 ticket is settled. The manifest shape was
checked against the installed PlatformIO core (6.1.19) source and the
current developer docs (docs.platformio.org, "Custom Development
Platforms"):

- `platform.json` `packages[].version` accepts a direct URL; the docs
  example is `"version": "https://github.com/user/repo.git"`. The
  toolchain package is referenced by its release URL, per D-6.
- Board manifests require `name`, `url`, `vendor`; `build.mcu`,
  `build.f_cpu` and `upload.maximum_*` are the fields the builder and the
  size check read.
- The builder is `builder/main.py`, loaded by PlatformIO's SCons wrapper;
  `env.BoardConfig()`, `env.PioPlatform().get_package_dir()` and
  `env.MatchSourceFiles()` are the documented extension points.
