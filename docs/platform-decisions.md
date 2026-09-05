# Platform decisions

## Upload: minipro (TL866) and pk2cmd (PICkit2/3/3.5) both landed

**Superseded 2026-09-05.** The original v1 call below rejected `pk2cmd`
and `ipecmd` because both are Microchip's own tools, and the platform's
reason to exist is a build path with no Microchip downloads (design doc
31 D-5). It did not anticipate genuinely independent, non-Microchip open
source flashing tools for hardware hobbyists already own, and it did not
distinguish "a download from Microchip's own servers" from "a
community-maintained GitHub fork we point a script at."

| Device | Tool | License | Independent of Microchip |
|---|---|---|---|
| TL866A / TL866II Plus (not TL866CS, no ICSP header) | [`minipro`](https://gitlab.com/DavidGriffith/minipro) | GPL | Yes, fully (XGecu hardware, independent reimplementation) |
| PICkit2 / PICkit3 / "PICkit3.5" clones ("3.5" is clone-vendor branding for the PICkit3 protocol, not a Microchip designation) / PKOB | [`jaka-fi/pk2cmd`](https://github.com/jaka-fi/pk2cmd) | Microchip's own license (reproduced in full in `docs/pk2cmd-LICENSE.md`) | No, and not treated as if it were. Decided: full first-class support anyway, not a bring-your-own-binary carve-out, on the reasoning recorded in `docs/pk2cmd-LICENSE.md`; not a Microchip download in the D-5 sense, since it is a third-party-maintained fork we fetch from GitHub, never Microchip's own site or an account/EULA click-through. |

`minipro`/TL866 landed first as the pathfinder (`epic-platformio#11`):
the cleanest of the two, one unambiguous tool, no firmware-bootstrap
gotchas. `pk2cmd`/PICkit2+3+3.5 followed (`epic-platformio#12`), picking
`jaka-fi/pk2cmd` specifically: most actively maintained fork found (most
stars, most recent commits of the candidates checked), explicit
PICkit2+3+PKOB support, and its own README already states its license
situation as plainly as we'd want to ourselves ("THE CODE IN THIS
REPOSITORY IS NOT FREE SOFTWARE"). Known gotcha, load-bearing enough to
repeat here: PICkit3/PKOB need a one-time Windows-only "scripting
firmware" update before any Linux tool, including this one, can drive
them at all.

**Neither tool is vendored as a PlatformIO package**, meaning neither
ships inside a `tool-*` package installed automatically by `pio pkg
install`, the shape `framework-epichal`/`toolchain-epiccc` use. Both
still need a separate step:

- `minipro`: no Debian/Ubuntu package exists (checked directly, absent
  from `apt-cache`); build it from source, documented in
  `docs/getting-started.md#upload`. `builder/main.py` finds it on `PATH`
  or via `EPIC8_MINIPRO_PATH`.
- `pk2cmd`: `scripts/install-pk2cmd.sh` downloads a checksum-pinned
  release from `jaka-fi/pk2cmd`, verified against a hash recorded in the
  script, and installs it without a build step. This is a real, tested
  step up from "build it yourself": the script was run end to end
  against the real v1.27.01 release during development, including the
  real binary's `-B`/`-P`/`-F`/`-M` invocation confirmed by reading its
  own `--help` output and its device database directly (grepped for
  `PIC16F877A`/`PIC16F887`/`PIC18F4550`), not assumed from documentation
  alone. `builder/main.py` finds it at the script's install location by
  default, or via `EPIC8_PK2CMD_PATH`/`EPIC8_PK2CMD_DIR`.

A real `tool-*` package (an epic-platformio-hosted release, installed
automatically by `pio pkg install`, matching PIO-2's shape exactly) is a
later, separate effort for either tool, not part of landing the upload
target itself: it means standing up a packaging workflow like
`.github/workflows/package.yml` already does for `toolchain-epiccc`, and
for `pk2cmd` specifically, re-hosting a copy of Microchip-licensed
software under our own releases rather than pointing at upstream's,
which deserves its own deliberate decision rather than arriving as a
side effect of this one.

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
