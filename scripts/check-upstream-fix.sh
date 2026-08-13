#!/usr/bin/env bash
set -Eeuo pipefail

upstream_dir=${1:?Usage: check-upstream-fix.sh UPSTREAM_DIR}
series_page="$upstream_dir/src/pages/collection/series/SeriesImages.tsx"
series_mutations="$upstream_dir/src/core/react-query/series/mutations.ts"
series_put_endpoint="axios.put(\`Series/\${seriesId}/Images/\${imageType}\`"
series_delete_endpoint="axios.delete(\`Series/\${seriesId}/Images/\${imageType}\`)"

if [[ ! -f "$series_page" || ! -f "$series_mutations" ]]; then
  printf 'error: upstream WebUI files are missing\n' >&2
  exit 1
fi

if grep -Fq 'useSetPreferredSeriesImageMutation' "$series_page" \
  || grep -Fq 'useUnsetPreferredSeriesImageMutation' "$series_page" \
  || grep -Fq "$series_put_endpoint" "$series_mutations" \
  || grep -Fq "$series_delete_endpoint" "$series_mutations"; then
  printf 'error: upstream already contains the preferred-series-image fix; retire this patch\n' >&2
  exit 1
fi

if ! grep -Fq 'useSetPreferredImageMutation' "$series_page" \
  || ! grep -Fq 'useUnsetPreferredImageMutation' "$series_page" \
  || ! grep -Fq 'mutate(selectedImage.ID' "$series_page"; then
  printf 'error: upstream preferred-image code changed; review and retire or update this patch\n' >&2
  exit 1
fi
