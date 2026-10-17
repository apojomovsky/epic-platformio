# Migration map: internal docs

Internal design history moved from `docs/` and `packages/` to
`docs/internals/` (epic-platformio#150). Each row maps a path that
existed on `master` before the move to its new path. Inbound links
from other repositories or old bookmarks can use this table to
redirect. Content is unchanged except for the link and path fixes
inside the moved files, the scripts and the code comments that name
them.

| Old path | New path |
|---|---|
| `docs/platform-decisions.md` | `docs/internals/platform-decisions.md` |
| `docs/packages.md` | `docs/internals/packages.md` |
| `packages/README.md` | `docs/internals/packages/README.md` |

Not moved, by design: `docs/getting-started.md` and
`docs/programmers/` (user flashing guides), `docs/user/` (user
reference), `packages/toolchain-epiccc/README.md` and
`packages/framework-epichal/README.md` (registry-rendered package
pages), and `AGENTS.md` (the agent file stays at the root).
