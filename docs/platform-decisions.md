# Platform decisions

## Boards: generated from epic-cc/epic-hal's own registries, every device, no curation

**Decision (PIO-6, epic-platformio#24).** `boards/*.json` is generated
(`scripts/gen_boards.py`) by joining epic-cc's device manifest (CC-7)
against epic-hal's part-to-family map and per-family `epiccc_sources`
declaration, one board per device either repo knows about, at whatever
capability level it actually has. No allowlist or denylist: a device
that would need curating out (e.g. a very low-resource baseline part) is
a decision for the user's own `platformio.ini`, not this repo's board
list.

Each board's `build.toolchains` and `build.framework_epichal_toolchains`
record the answer directly, and `builder/main.py` validates a project's
`board_build.toolchain`/`framework` choice against them at build time:
picking a combination the board doesn't support fails loudly, naming
what it does support, rather than silently building with the wrong
include set or resolving a toolchain binary the board can never use
correctly.

**The join key is the bare device name**, not a live call into either
toolchain: epic-cc's own device names in its manifest are already
canonical ("p" + epic-hal's own spelling, lowercased), a fixed
structural fact (epic-cc#428 / epic-hal#162), not a per-device guess.

**`url` is generated, not verified, for every board this script
synthesizes from scratch.** PlatformIO's own board schema requires a
non-empty `url`; the existing 3 hand-authored boards already used
`https://www.microchip.com/en-us/product/<PART>`, so newly generated
boards follow the same scheme rather than leaving the field out, but
this has not been individually confirmed to resolve for every part.

**Wired into the release pipeline (PIO-7, epic-platformio#25).** A
scheduled `boards-refresh` workflow regenerates `boards/*.json` against
the latest epic-cc and epic-hal releases daily (also `workflow_dispatch`,
pinnable to a specific tag pair), diffs the result against what's
committed, and opens a pull request when it differs instead of ever
committing to master directly, the same review gate as everything else
in this repo. The PR body (`scripts/summarize_boards.py`) reports added,
removed, and capability-changed boards, not a raw JSON diff. A second
run before the first is merged updates that same PR rather than opening
a duplicate.

`scripts/package_framework.py` packages every family bundle a release
actually publishes, discovered from each bundle's own
`epic-hal-sources.json` `"family"` field rather than a hardcoded list
(same for `package.yml`'s "framework" job, which now discovers the set
of family bundles to download from the epic-hal release's own asset
list before building). A board can still validly claim `framework =
epichal` support for a family whose HAL content genuinely has nothing to
build yet (e.g. a family manifest with zero HAL modules, or a module
that calls into a peripheral driver the epic-cc conformant source slice
doesn't include) — `builder/main.py` fails loudly naming that gap at
build time rather than silently miscompiling; this is a content gap for
epic-hal to close per family, not a packaging-pipeline bug.

## Toolchain: xc8 lands as a fully supported alternate, never vendored

**Decision (PIO-4, epic-platformio#22).** `board_build.toolchain = xc8`
builds with MPLAB XC8 instead of epic-cc, on any board this platform
ships, with or without `framework = epichal`. epic-cc stays the default:
nothing about the zero-Microchip-download pitch changes for a project
that never sets `board_build.toolchain`. This mirrors epic-cc's own
design doc D-5 ("epic-cc becomes epic-hal's default path; XC8 stays
supported") at the PlatformIO layer, and epic-hal's own build driver
(`epic_build.py`) already defaults to xc8 on its side, so this closes a
gap in platform-epic8 specifically, not a new position for the ecosystem.

**Never vendored, same reasoning as minipro/pk2cmd below, sharper.**
Microchip's EULA forbids redistributing XC8 at all (not merely "no
package exists," `pk2cmd`'s situation); `platform.json` carries no
`packages.*` entry for it, and never will. `builder/main.py` finds a
binary the user already installed, on `PATH` or via `EPIC8_XC8_PATH`, and
an optional `EPIC8_XC8_DFP_DIR` for a device family pack, the same
discovery shape as `EPIC8_MINIPRO_PATH`/`EPIC8_PK2CMD_PATH`. Documented in
`docs/getting-started.md#xc8`.

**Why now, why not earlier.** The framework package (`framework-epichal`)
platform-epic8 already downloads has shipped XC8-shaped sources
(`hal_sources`, `include/target`) since PIO-2, as the base every
epic-cc-specific slice (`epiccc_sources`, `include/epiccc`) is carved out
of; only `builder/main.py` never read them. XC8 support was therefore a
builder gap, not a packaging or framework one.

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
