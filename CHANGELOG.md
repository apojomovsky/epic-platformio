# Changelog

All notable changes to this project are documented here, generated from
Conventional Commits. Dates are UTC.
## [toolchain-epiccc-v0.3.0] - 2026-09-13

### Bug Fixes

- Remove em-dash from platform-decisions.md

- Pin toolchain-epiccc package.json to released 0.1.0

- Don't regress the live pointer on an out-of-order re-cut

- Dedupe write-back, fix duplicate changelog entries, avoid races

- Use semver order for old_upstream_tag and stop truncating multi-version rollups


### Documentation

- Require a separate code review before takeoff

- Board-track every filed issue

- Rewrite as a two-speed pitch, matching epic-cc/epic-hal

- Stop asserting epic-cc's backend coverage as a fact here

- Tighten the package.yml header comment, note the race guard

- Describe the automated publish write-back and CI version check


### Features

- Rebundle on epic-cc v0.1.0 and epic-hal v0.5.0

- Wire pio run -t upload to minipro for TL866A/TL866II Plus

- Wire pio upload to pk2cmd-family tools

- Add git-cliff config and the initial CHANGELOG.md

- Finish the framework job and write back versions on publish

- Xc8 as an alternate builder toolchain


### Miscellaneous

- Fail the build when package versions drift


### Other

- Merge pull request #10 from apojomovsky/feat/5-package-rebundle

feat(packages): rebundle on epic-cc v0.1.0 and epic-hal v0.5.0 (#10)

- Merge pull request #13 from apojomovsky/feat/upload-minipro

feat(upload): wire pio run -t upload to minipro for TL866A/TL866II Plus (#13)

- Merge pull request #15 from apojomovsky/feat/12-pk2cmd-upload

feat(upload): wire pio upload to pk2cmd-family tools (#15)

- Merge pull request #16 from apojomovsky/docs/review-gate

docs: require a separate code review before takeoff (#16)

- Merge pull request #17 from apojomovsky/docs/board-tracking-rule

docs: board-track every filed issue (#17)

- Merge pull request #18 from apojomovsky/docs/readme-refresh

docs(readme): rewrite as a two-speed pitch, matching epic-cc/epic-hal (#18)

- Merge pull request #19 from apojomovsky/docs/readme-fixes

docs(readme): stop asserting epic-cc's backend coverage as a fact here (#19)

- Merge pull request #21 from apojomovsky/ci/20-cliff-release

ci(release): finish framework packaging, fix version drift, git-cliff changelog and rollup (#21)

- Merge pull request #27 from apojomovsky/feat/22-xc8-toolchain

feat(platform): xc8 as an alternate builder toolchain (#27)

### Upstream: epic-cc v0.1.0 -> v0.3.0

#### [0.3.0] - 2026-09-13

##### Bug Fixes

- Scope release artifact download and move artifact actions off node20 (#379)
- Sweep PIC14 and PIC14E DFP packs, map baseline arch names (#380)
- Sweep baseline DFP pack, derive fsr_bank_bits, gate DCR to pic18 (#381)
- Keep wide-compare skip chains atomic on 0xFF folds (#384)
- Floor variadic va regions to one byte for va_start base (#400)
- Route cut-release through a PR to satisfy the master ruleset (#414)
- Use a PAT for cut-release so its release PR checks actually run (#419)

##### Documentation

- Fix factual errors found by a real fact-check pass (#378)
- Retire runbook sections 2-6 in favor of add-device.sh (#385)
- Record P7 soft-float as documented non-goal (#386)
- Non-goal rationales plus landed-state table refresh (#388)
- Conclude printf putchar-sink probe as SDCC limitation (#390)
- Common_ram classification design for the 6 excluded PIC14 devices (#397)

##### Features

- P6 32-bit long add/sub/shift/compare plus mul/div routines (#382)
- Freestanding malloc/free plus honest Tier-2 probe (#392)
- Math.h library and honest Tier-2 probe (#389)
- Onboard 15 catalog-selected high-tier devices (#394)
- Add p12f683 (PIC12F683) (#396)
- Implement ADR-034 single-region common_ram split (#399)
- PIC16F74 full interrupt support (docs/39 D-2) (#401)
- Pic-baseline differential fuzz gate and PicBaseline arm in run_pic (#402)
- Git-cliff changelog and automated release-cutting workflow (#404)
- Mid-range groundwork, exemplar parts and the ISR carve-out widening fix (#412)
- Add p16f54 (#413)
- Add the nine PIC18 exemplar parts (#415)
- Gputils crosscheck reconciliation for ini-sourced small parts (#418)
- Onboard the remaining classic PIC16 mid-range parts (#421)
- Onboard the remaining 16F5x baseline parts (#424)
- Onboard the remaining requested PIC18 parts (#425)
#### [0.2.0] - 2026-09-10

##### Bug Fixes

- Wire emit_commutative through the W-tracking cache (#218)
- Gen-device.py mis-generates PIC18 config and RAM layout (#231)
- Drop the hardcoded part name from the pic14 xtal_hz panic (#233)
- Derive the PIC18 access-bank boundary from device data (#234)
- Refuse to write pack = unknown in gen-device.py (#239)
- Reload the subtrahend in const-LHS sub fold (#242)
- Count __start init and module-asm words in page-0 base (#244)
- Disable fp-contract so float mul+add compiles (#281)
- Stop base apt-get changes from busting the clang-builder cache (#280)
- Isolate gputils/SDCC's from-source builds from unrelated dev deps (#293)
- Non-root dev image default, defense in depth (#294)
- Resolve PIC18 sim PANIC; document recursion (#296)
- Add ELA-aware parse_hex_pic14e for the PIC14E gate hexes (#307)
- Default the optional PIC14E config fields to erased values (#308)
- Lower i1 loads and stores as bytes (#310)
- Isolate local clang cache from docker system/builder prune (#312)
- Sweep the PIC18Fxxxx DFP pack, fix alias-table gaps (#361)
- Stop compat ISR W save from clobbering FSR0H's snapshot (#363)
- Stage indirect store values before the FSR setup (#367)
- Restore compat ISR SFRs before the retval backup (#369)
- Halve ini ROMSIZE for PIC18, it states bytes not words (#371)

##### Documentation

- ADR-027, a bank-aware instruction scheduler pass (#219)
- Write docs/32-adding-a-device.md, the same-core device runbook (#235)
- PIC14E (Enhanced Mid-range) backend port design (#236)
- Land the phase 2-4 design doc as docs/34 (#241)
- Revise the port design per independent review (#243)
- Require a separate code review before takeoff (#254)
- Track PIC baseline core as a future backend candidate (#256)
- Record settled phase 2-4 scope, fix full -g mechanism (#260)
- Board-track every filed issue (#262)
- SDCC parity epic design (docs/35) (#271)
- PIC18 float-routine access-bank frame allocation (design) (#285)
- Robustness test strategy beyond differential fuzzing (docs/36) (#292)
- PIC baseline core port design (docs/37) (#321)
- Device onboarding hardening design (docs/38) (#332)
- State peripheral-blindness and four-core scope decisions (#341)
- Rewrite as a two-speed pitch instead of a design doc (#377)

##### Features

- Add the crates/schedule skeleton as an identity transform (#221)
- Implement the phase-1 singleton-excursion swap (#222)
- Implement the phase-2 dead-W bundle hoist (#223)
- Add PIC18F2550 as a second PIC18 device (#232)
- Address-to-line table via --line-table (#240)
- PIC14E 193x device TOMLs and config hex-path fix (#245) (#255)
- PIC14E encoder and sim core (pic14e P1) (#261)
- Integer spine and BSR/MOVLB banking (pic14e P2) (#264)
- P3 pointers/arrays/structs via FSR0/1 + linear addressing (#272)
- Typed variable table via full -g debug metadata (#274)
- PIC14 debugger control surface: run_until, registers, memory (#275)
- SDCC 4.6.0 oracle + differential harness + baseline (P0) (#276)
- Support double as f32 on msp430 (PIC18 parity) (#277)
- P4 const in flash via RETLW (#278)
- Thread double through call/param/return/binop (#279)
- Interrupts with hardware context save (P5) (#283)
- P6 32-bit long and mul/div routines (#284)
- Gdbstub adapter plus ELF-DWARF sidecar as epic-cc-gdbserver (#282)
- Pin PIC18 float routines into the access-bank window; ship %f printf (#295)
- P7 soft-float f32 routines (#297)
- PIC14E differential fuzz gate (P8) (#298)
- PIC14E differential parity on 16F1938 (#302)
- Coverage-guided fuzz target for irparse parser (Lane B) (#311)
- Arbitration gate with sdcc-known-bugs.toml (docs/35 5.2) (#313)
- Valid comparison protocol, ratio gate, P0 closure (#319)
- Wire w_holds into const-table index and i8 add stores (#320)
- SDCC regression-suite pass rate as nightly context (Tier 3) (#322)
- Pic-baseline core variant and p12f509 TOML, firewall-only (#340)
- Real %f, EEPROM and const-pointer probes with oracle hardening (#353)
- PIC8 flash-generation part catalog with popularity tiers (#355)
- Gen-device.py --sweep breadth-proofing mode (#358)
- PIC baseline P1 encoder and sim core (#359)
- Two-vector priority interrupts (#360)
- Add-device.sh one-command device onboarding wrapper (#364)
- Integer spine with D-2 FSR bank-bit reassertion (#365)
- P3 pointers, arrays, structs via FSR flat addressing (#368)
- Per-context float frames with banked recipes (#370)
- P4 const in flash via RETLW, 256-word ceiling (#374)
- Add PIC16F628A and scattered config mask support (#373)

##### Miscellaneous

- Skip build+test loop on doc-only PRs (#263)
- Make image idempotent to skip the --load re-export (#315)
- Production-ready src comments without planning-stage prose (#354)
- Ruff auto-linter plus clean python baseline (#376)

##### Testing

- Pin bit-fields and unions with e2e tests (PIC14 parity) (#300)
- Lane D idempotence, fixpoint, and determinism checks (#288) (#305)
- Compile-time bound for adversarial BANKSEL dataflow (Lane G) (#306)
- Resource-exhaustion boundary tests (Lane F) (#309)
- Pin volatile store ordering and count (docs/36 lane E) (#316)
- Lane C mutants-killing tests and triage checklist (#317)

## [toolchain-epiccc-v0.1.0] - 2026-09-04

### Bug Fixes

- Blink toggles an LED, HAL example blocks on the tick


### Features

- Publish framework package, add examples and docs


### Other

- Merge pull request #9 from apojomovsky/feat/4-registry-examples-docs

feat(platform): PIO-3 examples, docs and framework package (#9)

## [toolchain-epiccc-v0.0.4] - 2026-09-01

### Bug Fixes

- Forward include dirs, track headers, handle program target


### Features

- Add platform core, builder and board definitions


### Other

- Merge pull request #8 from apojomovsky/feat/3-platform-core

feat(platform): add platform core, builder and board definitions (#8)

## [toolchain-epiccc-v0.0.3] - 2026-08-31

### Bug Fixes

- Address review, harden workflow and smoke


### Documentation

- Correct hook and CI gate claims in AGENTS.md

- Rename platform to platform-epic8, registry id epic8


### Features

- Wrap epic-cc bundles as toolchain-epiccc package


### Miscellaneous

- Initial empty commit

- Bootstrap repository scaffolding

- Fix JSON lint when platform.json is absent


### Other

- Merge pull request #5 from apojomovsky/feat/1-repo-bootstrap

chore: bootstrap repository scaffolding (#5)

- Merge pull request #6 from apojomovsky/docs/rename-epic8-platform

docs: rename platform to platform-epic8, registry id epic8 (#6)

- Merge pull request #7 from apojomovsky/feat/2-package-plumbing

feat(packages): wrap epic-cc bundles as toolchain-epiccc package (#7)
