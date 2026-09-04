# framework-epichal

PlatformIO package wrapping the `epic-hal` family bundles.

## Layout

```
framework-epichal/
  package.json
  epic-common/
  epic-bus/
  epic-...
  pic16f87xa-hal/
  pic16f88x-hal/
  pic18fxx5x-hal/
  epic-hal-sources-pic16f87xa.json
  epic-hal-sources-pic16f88x.json
  epic-hal-sources-pic18fxx5x.json
  VERSION
```

The package is the union of every supported family bundle: the shared
modules are copied once, each family's hal dir is kept separate, and each
family's source manifest is renamed per family so the builder can pick the
one matching the board's MCU. Each source manifest also carries the
`epiccc_sources` slice, the epic-cc conformant source set, and the
`src/epiccc/` files are copied in from the epic-hal checkout (the release
bundles omit them).

The builder wires the framework into the include path and sources; no
compilation happens inside the package itself.

## Version mapping

Package version equals the upstream `epic-hal` tag with the leading `v`
stripped (`v0.4.0` -> `0.4.0`). A packaging-only fix bumps the package patch
version, recorded in `packages/versions.json` (D-6).
