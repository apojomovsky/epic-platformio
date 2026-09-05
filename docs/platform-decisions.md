# Platform decisions

## Upload: minipro (TL866) and pk2cmd (PICkit2/3) both landed

**Superseded 2026-09-05.** The original v1 call below rejected `pk2cmd`
and `ipecmd` because both are Microchip's own tools, and the platform's
reason to exist is a build path with no Microchip downloads (design doc
31 D-5). It did not anticipate genuinely independent, non-Microchip open
source flashing tools for hardware hobbyists already own: cheap
"hacker's" programmers sold on AliExpress split cleanly by how
independent their host-side tooling is from Microchip.

| Device | Tool | License | Independent of Microchip |
|---|---|---|---|
| TL866A / TL866II Plus (not TL866CS, no ICSP header) | [`minipro`](https://gitlab.com/DavidGriffith/minipro) | GPL | Yes, fully (XGecu hardware, independent reimplementation) |
| PICkit2 / PICkit3 / "PICkit3.5" clones ("3.5" is clone-vendor branding for the PICkit3 protocol, not a Microchip designation) | `pk2cmd`-family (`pk2cmd-minus`, `PICkitminus`) | Microchip's own restrictive license | No, but the restriction reads as being about the *target chip* being genuine Microchip silicon, not the programmer's brand, and every board here targets genuine Microchip parts. Decided: full first-class support, not a bring-your-own-binary carve-out, revisited only if something concrete (redistribution terms on a specific fork) forces it. |

`minipro`/TL866 landed first as the pathfinder (`epic-platformio#11`): the
cleanest of the two, one unambiguous tool, no firmware-bootstrap gotchas.
`pk2cmd`/PICkit2+3 landed as `epic-platformio#12`, wire-compatible with
the same dispatcher shape. A known gotcha there is that some PICkit3 clones
need a one-time Windows-only firmware update before any Linux tool can
drive them, documented in `docs/getting-started.md#upload`.

**Neither tool is vendored.** Neither `minipro` nor `pk2cmd` has a
Debian/Ubuntu package (checked directly: absent from `apt-cache`), and
building/hosting our own prebuilt cross-platform binaries is a
distribution project on the scale of epic-cc's
`docs/30-distribution-design.md`, not something to fold into wiring an
upload target. `builder/main.py` finds a binary the user already built,
on `PATH` or via an env var override (`EPIC8_MINIPRO_PATH` /
`EPIC8_PK2CMD_PATH`), and the build steps are documented in
`docs/getting-started.md#upload`. This is a deliberate amendment to
the "belongs in a `tool-*` package" note below: a `tool-*` package that
vendors a real prebuilt binary is a later, separate effort, not part of
landing the upload target itself.

**A bootloader protocol** remains rejected: real work with no hardware to
validate against in this repo, and no consumer asking for it.

### Original v1 decision (2026-08, for history)

`pio run -t upload` failed with a clear message: the HEX is the
deliverable and flashing is left to the user's own programmer (pk2cmd,
ipecmd, a bootloader). `pk2cmd`/`ipecmd` wrappers were rejected because
both are Microchip tools, and wrapping them would make the platform
depend on the very downloads it exists to avoid (design doc 31 D-5). The
decision was recorded so it would not be relitigated per PR, and left a
note for whoever picked this back up: when a programmer integration
lands, it belongs in a `tool-*` package (PIO-2 shape), not the platform
core. See the superseding section above for what actually changed.

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
