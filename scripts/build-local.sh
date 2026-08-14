#!/usr/bin/env bash
set -Eeuo pipefail

root_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
upstream_url=${UPSTREAM_URL:-https://github.com/ShokoAnime/Shoko-WebUI.git}
upstream_ref=${UPSTREAM_REF:-master}
repository=${SHOKO_REPOSITORY:-crowquillx/shoko-webui-patched}
work_dir=${WORK_DIR:-"$root_dir/.local"}
webui_dir="$work_dir/webui"
output_dir=${OUTPUT_DIR:-"$root_dir/build"}
patch_file="$root_dir/patches/series-image-preferred.patch"

command -v git >/dev/null || { printf 'error: git is required\n' >&2; exit 1; }
command -v pnpm >/dev/null || { printf 'error: pnpm 11 is required\n' >&2; exit 1; }
command -v zip >/dev/null || { printf 'error: zip is required\n' >&2; exit 1; }
command -v sha256sum >/dev/null || { printf 'error: sha256sum is required\n' >&2; exit 1; }

rm -rf -- "$webui_dir"
mkdir -p -- "$work_dir"
git clone --depth 1 --branch "$upstream_ref" "$upstream_url" "$webui_dir"
git -C "$webui_dir" fetch --no-tags origin "$upstream_ref"
git -C "$webui_dir" checkout --detach FETCH_HEAD

upstream_commit=$(git -C "$webui_dir" rev-parse HEAD)
"$root_dir/scripts/check-upstream-fix.sh" "$webui_dir"
git -C "$webui_dir" apply --3way "$patch_file"
"$root_dir/scripts/verify-patched.sh" "$webui_dir"

base_version=$(node -p "require('$webui_dir/package.json').version.replace(/-.*/, '')")
if [[ ! "$base_version" =~ ^[0-9]+(\.[0-9]+){0,2}$ ]]; then
  printf 'error: package version is not System.Version-compatible: %s\n' "$base_version" >&2
  exit 1
fi
local_number=${LOCAL_BUILD_NUMBER:-$(date -u +%s)}
if [[ ! "$local_number" =~ ^[0-9]+$ ]]; then
  printf 'error: LOCAL_BUILD_NUMBER is not numeric: %s\n' "$local_number" >&2
  exit 1
fi
version="${base_version}-dev.${local_number}"
node - "$version" "$webui_dir/package.json" <<'NODE'
const fs = require('node:fs');
const [version, packagePath] = process.argv.slice(2);
const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
packageJson.version = version;
fs.writeFileSync(packagePath, `${JSON.stringify(packageJson, null, 2)}\n`);
NODE
[[ "$(node -p "require('$webui_dir/package.json').version")" == "$version" ]]

pnpm --dir "$webui_dir" install --frozen-lockfile
pnpm --dir "$webui_dir" tscheck
pnpm --dir "$webui_dir" lint --quiet
pnpm --dir "$webui_dir" build
python3 "$root_dir/scripts/validate-build.py" "$webui_dir/dist" --version "$version"

min_server_version=$(node -p "require('$webui_dir/dist/version.json').minimumServerVersion")
asset="$output_dir/Shoko-WebUI-v${version}.zip"
mkdir -p -- "$output_dir"
rm -f -- "$asset"
(
  cd -- "$webui_dir/dist"
  zip -q -r "$asset" . -x '*.map' '**/*.map'
)
if unzip -Z1 "$asset" | grep -E '\.map$' >/dev/null; then
  printf 'error: the WebUI archive contains a source map\n' >&2
  exit 1
fi
python3 "$root_dir/scripts/validate-build.py" "$asset" --version "$version"
checksum="sha256:$(sha256sum "$asset" | cut -d ' ' -f 1)"
notes="$work_dir/release-notes.txt"
printf 'Patched Shoko WebUI local build.\n\nSource commit: %s\nPatch: %s\nMinimum Server Version: **%s**\n' \
  "$upstream_commit" "$(sha256sum "$patch_file" | cut -d ' ' -f 1)" "$min_server_version" > "$notes"
download_url="https://github.com/${repository}/releases/download/v${version}/Shoko-WebUI-v${version}.zip"
python3 "$root_dir/scripts/update-manifest.py" "$output_dir/manifest.json" \
  --version "$version" \
  --commit "$upstream_commit" \
  --tag "v${version}" \
  --download-url "$download_url" \
  --checksum "$checksum" \
  --min-server-version "$min_server_version" \
  --release-notes "$notes"
python3 "$root_dir/scripts/validate-manifest.py" "$output_dir/manifest.json" --repository "$repository"
printf 'built %s\nmanifest %s\n' "$asset" "$output_dir/manifest.json"
