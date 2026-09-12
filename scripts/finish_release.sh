#!/usr/bin/env bash
# Shared write-back for a just-published package release: sync
# packages/versions.json, packages/<name>/package.json and platform.json,
# roll the upstream repo's CHANGELOG.md section into this repo's own
# CHANGELOG.md, and commit + push the result to master. Used by both the
# toolchain and framework jobs in .github/workflows/package.yml so this
# logic, and any fix to it, only has to exist once.
#
# Usage:
#   finish_release.sh <package> <pkg_ver> <upstream_tag> <owner/upstream-repo> \
#     <release-asset-name> [upstream_url_linux upstream_url_windows]
#
# The last two positional args are toolchain-epiccc only (per-system
# bundle URLs recorded in packages/versions.json); omit them for
# framework-epichal.
set -euo pipefail

package="$1"
pkg_ver="$2"
upstream_tag="$3"
upstream_repo="$4"
asset_name="$5"
upstream_url_linux="${6:-}"
upstream_url_windows="${7:-}"
upstream_name="${upstream_repo#*/}"
repo_tag="${package}-v${pkg_ver}"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

sync_args=(--package "$package" --pkg-version "$pkg_ver" --upstream-tag "$upstream_tag" --asset-name "$asset_name")
if [ -n "$upstream_url_linux" ]; then
  sync_args+=(--upstream-url-linux "$upstream_url_linux" --upstream-url-windows "$upstream_url_windows")
fi
old_upstream_tag="$(python3 scripts/sync_versions.py "${sync_args[@]}" | sed -n 's/^old_upstream_tag=//p')"

python3 scripts/strip_stale_unreleased.py --changelog CHANGELOG.md
git-cliff --config cliff.toml --tag "$repo_tag" --unreleased --prepend CHANGELOG.md

if gh api "repos/${upstream_repo}/contents/CHANGELOG.md?ref=${upstream_tag}" \
     --jq '.content' > /tmp/upstream-changelog.b64 2>/tmp/gh-api.err; then
  base64 -d /tmp/upstream-changelog.b64 > /tmp/upstream-changelog.md
else
  echo "no ${upstream_name} CHANGELOG.md at ${upstream_tag} yet: $(cat /tmp/gh-api.err)"
  : > /tmp/upstream-changelog.md
fi

# The upstream changelog and this git-log fallback are both best-effort:
# a network blip or a not-yet-merged sibling PR must not fail a release
# that has already been built, smoke-tested and published. rollup_changelog.py
# falls back to a placeholder line when neither source is available.
fallback_args=()
if [ ! -s /tmp/upstream-changelog.md ] && [ -n "$old_upstream_tag" ]; then
  if git clone --quiet --filter=blob:none --no-checkout "https://github.com/${upstream_repo}.git" /tmp/upstream-hist 2>/tmp/clone.err; then
    git -C /tmp/upstream-hist log --oneline "${old_upstream_tag}..${upstream_tag}" > /tmp/upstream-shortlog.txt || true
    fallback_args=(--fallback-log /tmp/upstream-shortlog.txt)
  else
    echo "could not clone ${upstream_repo} for a fallback log: $(cat /tmp/clone.err)"
  fi
fi

old_tag_args=()
if [ -n "$old_upstream_tag" ]; then
  old_tag_args=(--old-upstream-tag "$old_upstream_tag")
fi

python3 scripts/rollup_changelog.py \
  --changelog CHANGELOG.md \
  --repo-tag "$repo_tag" \
  --upstream-name "$upstream_name" \
  --new-upstream-tag "$upstream_tag" \
  "${old_tag_args[@]}" \
  --upstream-changelog /tmp/upstream-changelog.md \
  "${fallback_args[@]}"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git add packages/versions.json "packages/${package}/package.json" platform.json CHANGELOG.md
git commit -m "chore(release): ${package} v${pkg_ver}"
git push origin HEAD:master
