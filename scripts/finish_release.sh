#!/usr/bin/env bash
# Shared write-back for a just-published release: sync versions.json,
# package.json and platform.json, roll the upstream CHANGELOG.md section
# in, commit and push to master. Used by both package.yml jobs so this
# logic only exists once.
#
# finish_release.sh <package> <pkg_ver> <upstream_tag> <owner/upstream-repo> \
#   <release-asset-name> [upstream_url_linux upstream_url_windows]
# The last two args are toolchain-epiccc only, omit for framework-epichal.
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

# master has no branch protection, and several agents work this repo in
# parallel, so an unrelated PR merging between this job's checkout and its
# push shows up as a plain non-fast-forward, not a real conflict in the
# common case (this commit only touches version/changelog bookkeeping
# files an unrelated PR is unlikely to also touch): rebase and retry
# rather than losing an already-built, already-published release. A
# genuine conflict still aborts loudly via set -e in the rebase itself.
for attempt in 1 2 3 4 5; do
  if git push origin HEAD:master; then
    exit 0
  fi
  echo "push rejected (attempt ${attempt}/5), fetching and rebasing onto origin/master"
  git fetch origin master
  git rebase origin/master
done
echo "::error::could not push the release commit after 5 attempts" >&2
exit 1
