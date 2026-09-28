# Platform decisions

## Boards: generated from epic-cc/epic-hal's own registries, curated beta set plus `boards-experimental/`

**Amended for the beta (PIO-2, epic-platformio#45; docs/46 D-2).** The
original decision below generated one board per device into `boards/`, with
no allowlist or denylist. The beta makes a support promise per board, which
a generated list cannot back, so the set is now split in two:

- **`boards/`** holds the six curated beta parts (`pic16f877a`,
  `pic16f887`, `pic16f628a`, `pic12f675`, `pic16f1937`, `pic18f4550`), each
  carrying what the registries do not know: `upload.maximum_size` and
  `upload.maximum_ram_size` from epic-cc's device TOMLs, `upload.devices.<tool>`
  with the name that tool itself matches on (minipro's `infoic.xml`,
  pk2cmd's `PK2DeviceFile.dat`, picpro's `chipdata.cid`), the D-9 hazard
  facts (`upload.hazards`: PGM pin or LVP scheme, the OSCCAL word, the
  bandgap bits), and a `support` field (`simulator` until D-11's silicon
  sign-off flips a green row to `hardware`, epic-platformio#52).
- **`boards-experimental/`** holds every other device at whatever
  capability level it has, and is documented and delivered as
  copy-into-your-project files: PlatformIO reads a project-local `boards/`
  natively and does not read a platform subdirectory other than `boards/`,
  so nothing unverified is advertised in `pio boards`.

The split is by device, and the generator decides it from one table
(`scripts/gen_boards.py`'s `CURATED`), so a part promoted to the beta set
is one entry there plus the facts behind it.

**Curated ids follow the chip's own name** (PlatformIO's convention,
`pic16f877a`), while `build.mcu` keeps epic-cc's p-prefixed device name
(`p16f877a`), the split the builder already relies on. A curated board's
`pic16f877a.json` and an experimental board's `p16f877a.json` therefore name
the same device under two different file names; the generator never writes
one device into both directories.

**The rest of this section (generation, capability fields, the join key,
the generated `url`, the PIO-7 wiring) is unchanged and applies to both
sets.**

**Decision (PIO-6, epic-platformio#24).** `boards/*.json` is generated
(`scripts/gen_boards.py`) by joining epic-cc's device manifest (CC-7)
against epic-hal's part-to-family map and per-family `epiccc_sources`
declaration, one board per device either repo knows about, at whatever
capability level it actually has.

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
scheduled `boards-refresh` workflow regenerates the curated `boards/` set
and `boards-experimental/` against
the latest epic-cc and epic-hal releases daily (also `workflow_dispatch`,
pinnable to a specific tag pair), diffs the result against what's
committed, and opens a pull request when it differs instead of ever
committing to master directly, the same review gate as everything else
in this repo. The PR body (`scripts/summarize_boards.py`) reports added,
removed, and capability-changed boards, not a raw JSON diff. Each run
pushes a fresh, timestamped branch (never force-pushes a shared one,
per this repo's own no-force-push rule) and closes any earlier run's
still-open PR as superseded rather than leaving two open at once. A
`concurrency` group serializes overlapping runs (a schedule firing
mid-`workflow_dispatch`, say) so two runs can never race to supersede
each other's freshly opened PR.

**[VERIFY]** Opening a PR from a workflow needs "Allow GitHub Actions
to create and approve pull requests" enabled in this repo's own Actions
settings; `boards-refresh.yml`'s `permissions:` block requests what it
needs, but that repo-level toggle is outside any workflow file's
control and has not been independently confirmed on.

`scripts/package_framework.py` packages every family bundle a release
actually publishes, discovered from each bundle's own
`epic-hal-sources.json` `"family"` field rather than a hardcoded list
(same for `package.yml`'s "framework" job, which now discovers the set
of family bundles to download from the epic-hal release's own asset
list before building). A board can still validly claim `framework =
epichal` support for a family whose HAL content genuinely has nothing to
build yet (e.g. a family manifest with zero HAL modules, or a module
that calls into a peripheral driver the epic-cc conformant source slice
doesn't include), `builder/main.py` fails loudly naming that gap at
build time rather than silently miscompiling; this is a content gap for
epic-hal to close per family, not a packaging-pipeline bug.

## Distribution: `platform.py` picks the host's toolchain, tools arrive on selection

**Decision (PIO-1, epic-platformio#44).** `platform.py` is the one place a
host-specific fact is resolved. It does two jobs and refuses nothing:

- **One toolchain package per host, remapped from the `platform.json`
  pin.** epic-cc ships a bundle per host while `platform.json` pins a
  single download URL per package, so the pin names one host's asset and
  `platform.py` swaps the host token in that asset's file name for the
  running machine's, the shape Community-PIO-CH32V uses. `platform.json`
  stays the only place a version is pinned (D-5, `docs/packages.md`) and
  the remap is a pure function of it, so the two hosts cannot drift to two
  versions the way two hand-kept pins would. Both Windows spellings
  PlatformIO can report (`windows_amd64`, `windows_x86_64`) resolve to the
  one Windows bundle this repo packs.

  **The remap answers on the `packages` property, not in
  `configure_default_packages`.** `PlatformBase.packages` rebuilds its dict
  from the manifest and re-applies a project's `platform_packages` pins on
  every read, so a value written into the manifest earlier is overwritten
  by the pin on the next read, and the installer (which reads through
  `get_package_spec`) would receive the pinned URL rather than the remapped
  one. Answering on the property also covers the global install path
  (`platformio platform install <url>`), which has no project attached and
  so never calls `configure_default_packages` at all.

  **A host with no bundle is passed through, not refused.** `packages` is
  read on uninstall, update and `pio pkg list` as well as on install, so
  raising there would leave the platform unremovable and unlistable outside
  the beta hosts, and would break a project on
  `board_build.toolchain = xc8`, which never needs the epic-cc toolchain.
  What stops the Linux artifact installing on a non-Linux host is the
  toolchain package's own `system` list.
- **A programmer tool package is pulled only when the project selects its
  protocol.** An explicit `upload_protocol` in the project's own
  configuration activates the package `PROTOCOL_TOOL_PACKAGES` names for
  it; the board's own `upload.protocol` default deliberately does not,
  since every board names one and treating it as a selection would make a
  plain `pio run` download a programmer the user may already have on PATH
  (the bring-your-own-binary path, "Upload" below). `custom` maps to
  nothing: it is the project's own `upload_command`.

**The tool packages do not exist yet** (epic-tools' `tool-minipro`,
`tool-pk2cmd`, `tool-picpro`; epic-platformio#40..#43). The hook is the
mapping plus a guard that only touches a package `platform.json` actually
declares, so a protocol named there but not yet carried is a no-op and its
build still finds the binary on `PATH`. The mapping names exactly the
protocols `builder/main.py` dispatches today, so it cannot activate a
package for a protocol the builder then rejects; `picpro` joins both ends
with epic-platformio#46. Two rules for whoever publishes these entries:
declare them with `"type": "tool"`, not `"uploader"`, because
`PlatformBase.configure_default_packages` enables every `uploader`-typed
package for any upload target and a `tool`-typed one stays under this
class's control; and keep each entry's name equal to the value in
`PROTOCOL_TOOL_PACKAGES`, or update that line with it.

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

**Device names moved under `upload.devices.<tool>` (PIO-2,
epic-platformio#45; docs/46 D-8).** The three original boards carried
`upload.minipro_device` / `upload.pk2cmd_device`; the curated set carries
one map, `upload.devices.<tool>`, with an entry per tool that supports the
part and none for a tool that does not (picpro has no 16F887 or 16F1xxx
entry, so those two boards carry no `devices.picpro`). `builder/main.py`
looks the name up there and refuses a protocol whose tool has no entry,
naming the tools that do rather than letting the programmer report an
unknown device. The per-part name is the exact spelling each tool matches
on, checked against the tool's own database rather than derived from the
part name: picpro lowercases its `-t` argument, minipro compares the
comma-separated `name` field of an `infoic.xml` entry exactly (a per-package
token such as `PIC16F1937@DIP40` when the part has no bare row), pk2cmd
its 28-byte `PartName`.

**Superseded 2026-09-05.** The original v1 call below rejected `pk2cmd`
and `ipecmd` because both are Microchip's own tools, and the platform's
original reason to exist was a build path with no Microchip downloads
(design doc 31 D-5, predating xc8 support; see PIO-4). It did not
anticipate genuinely independent, non-Microchip open source flashing tools
for hardware hobbyists already own: cheap
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
both are Microchip tools, and wrapping them would make the platform depend
on the very downloads the epic-cc default path exists to avoid (design doc
31 D-5, predating xc8 support). The
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
