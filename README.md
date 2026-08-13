# Patched Shoko WebUI feed

This repository builds a temporary patched release feed for
[Shoko-WebUI](https://github.com/ShokoAnime/Shoko-WebUI). It does not vendor the
WebUI. Each run checks out the current upstream `master`, applies the checked-in
patch, verifies the result, and builds a flat WebUI ZIP for Shoko.

The patch fixes **Set Preferred** and **Unset Preferred** on a series page. Both
operations use the series-scoped API endpoints. The set operation sends the
image UUID and source. The page refreshes its series image and series data
queries after either operation.

This is a temporary workaround. Remove this repository and restore the normal
Shoko-WebUI feed after the upstream fix is available.

## Shoko configuration

Set the client manifest URL to the raw `metadata` branch in this repository:

```text
SHOKO_CLIENT_MANIFEST_URL=https://raw.githubusercontent.com/crowquillx/shoko-webui-patched/metadata/manifest.json
```

Set this while using the patched feed so the bundled server WebUI does not
replace it at startup:

```text
SHOKO_WEBUI_AUTO_REPLACE=false
```

Restart Shoko after changing the settings. Use the Shoko WebUI update control
to install a release from the feed. The feed keeps the newest 30 development
entries, including their checksums, source commits, release tags, and notes.

## Updates and manual runs

The release workflow runs once each day. For a manual update, open GitHub
Actions, select **Build patched WebUI**, and select **Run workflow**. A run
does not build a second release when the upstream commit already has a release
in this repository.

For a local, non-publishing reproduction, use Node 22 or newer, pnpm 11, and
run:

```sh
./scripts/build-local.sh
```

The script leaves the source checkout under `.local/webui`, writes the ZIP and
manifest under `build/`, and never changes the separate upstream checkout.
The default release repository is `crowquillx/shoko-webui-patched`. Use
`SHOKO_REPOSITORY`, `UPSTREAM_URL`, `UPSTREAM_REF`, `WORK_DIR`, `OUTPUT_DIR`, or
`LOCAL_BUILD_NUMBER` to change local inputs.

The local manifest contains GitHub release URLs for the selected repository.
It is a verification artifact and is not published by the local script.

## Rollback

The metadata branch preserves prior entries. In the Shoko update control,
select a previous release when the server supports version selection. To pin a
previous feed, use a raw URL at an immutable metadata commit:

```text
https://raw.githubusercontent.com/<owner>/<repo>/<metadata-commit>/manifest.json
```

After rollback, keep `SHOKO_WEBUI_AUTO_REPLACE=false`. Restore the branch URL
when you want to receive new patched releases. To stop using the workaround,
remove `SHOKO_CLIENT_MANIFEST_URL` and restore the normal server settings.

## Patch retirement

`patches/series-image-preferred.patch` is intentionally small and applies only
to the three WebUI files needed for this fix. Both workflows run
`scripts/check-upstream-fix.sh` before patching. The check fails closed if
upstream already contains the series-scoped fix or if the relevant code moved;
there is no silent unpatched release.

When upstream fixes the issue:

1. Stop this workflow and stop using this manifest URL.
2. Confirm the upstream behavior and remove this temporary repository.
3. Let Shoko use the normal upstream WebUI feed.

Do not weaken the obsolete-fix check to keep this workaround running.

## Repository layout

- `patches/series-image-preferred.patch` — patch against upstream `master`.
- `UPSTREAM_COMMIT` — upstream commit used for the initial verification.
- `.github/workflows/release.yml` — scheduled and manually triggered release.
- `.github/workflows/ci.yml` — non-publishing patch and WebUI validation.
- `scripts/build-local.sh` — local reproduction and artifact build.
- `scripts/update-manifest.py` — atomic manifest update with history retention.
- `scripts/validate-manifest.py` — Shoko manifest validation.

The release workflow uses only the repository `GITHUB_TOKEN`. It requests
`contents: write` because it creates a release and updates `metadata`; CI uses
`contents: read`. No custom secrets are required.

## Initial verification

The initial base is recorded in `UPSTREAM_COMMIT`:

```text
e963cede52863d60d51d938e6c581d9b976aedc4
```

This is upstream `ShokoAnime/Shoko-WebUI` `master` at the time this repository
was created. The initial local build and manifest are generated under `build/`
by `scripts/build-local.sh`; build outputs are ignored because release assets
must come from GitHub Releases.
