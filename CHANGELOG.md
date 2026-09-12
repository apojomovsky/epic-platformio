# Changelog

All notable changes to this project are documented here, generated from
Conventional Commits. Dates are UTC.
## [Unreleased]

### Bug Fixes

- Remove em-dash from platform-decisions.md


### Documentation

- Require a separate code review before takeoff

- Board-track every filed issue

- Rewrite as a two-speed pitch, matching epic-cc/epic-hal

- Stop asserting epic-cc's backend coverage as a fact here


### Features

- Rebundle on epic-cc v0.1.0 and epic-hal v0.5.0

- Wire pio run -t upload to minipro for TL866A/TL866II Plus

- Wire pio upload to pk2cmd-family tools


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
