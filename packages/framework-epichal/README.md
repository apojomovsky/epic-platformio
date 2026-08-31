# framework-epichal

PlatformIO package wrapping the `epic-hal` family bundles.

Blocked by HAL-5 (distribution flip) for the final shape. Until that lands
the package scaffolding and tooling are in place but no framework package is
published.

## Layout (after HAL-5)

```
framework-epichal/
  package.json
  epic-common/
  epic-bus/
  epic-...
  pic16f87xa-hal/
  pic16f88x-hal/
  pic18fxx5x-hal/
  epic-hal-sources.json
  VERSION
```

The builder wires the framework into the include path and sources; no
compilation happens inside the package itself.

## Version mapping

Package version equals the upstream `epic-hal` tag with the leading `v`
stripped (`v0.4.0` -> `0.4.0`). A packaging-only fix bumps the package patch
version, recorded in `packages/versions.json` (D-6).
