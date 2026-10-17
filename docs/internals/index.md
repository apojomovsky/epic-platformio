# Internals

This directory holds epic-platformio's design history: the platform
decisions and the maintainer packaging notes behind the boards,
packages and upload tools the platform ships. It is for maintainers
who want to know why something is the way it is. User-facing material
(the [README](../../README.md), the [getting started
guide](../getting-started.md), the [user pages](../user/index.md) and
the [programmer guides](../programmers/minipro.md)) stays in `docs/`
and in each package.

Paths that moved here are listed in [MIGRATION.md](MIGRATION.md).

## Design decisions

- [platform-decisions](platform-decisions.md): why the boards are
  generated from epic-cc and epic-hal registries, why XC8 is never
  vendored, and how the upload tools were chosen.

## Maintainer packaging notes

- [packages](packages.md): how package versions map to upstream tags,
  how hosts are selected, and how the release pipeline builds and
  publishes the tarballs.
- [packages/README](packages/README.md): what each registry tarball
  contains. The user-facing copy lives in each package's own
  `README.md` under `packages/`.
