#!/usr/bin/env bash
set -Eeuo pipefail

webui_dir=${1:?Usage: verify-patched.sh WEBUI_DIR}
series_page="$webui_dir/src/pages/collection/series/SeriesImages.tsx"
series_mutations="$webui_dir/src/core/react-query/series/mutations.ts"
series_types="$webui_dir/src/core/react-query/series/types.ts"
put_endpoint="axios.put(\`Series/\${seriesId}/Images/\${imageType}\`"
delete_endpoint="axios.delete(\`Series/\${seriesId}/Images/\${imageType}\`)"

required_files=("$series_page" "$series_mutations" "$series_types")
for file in "${required_files[@]}"; do
  [[ -f "$file" ]] || { printf 'error: missing patched file: %s\n' "$file" >&2; exit 1; }
done

grep -Fq 'useSetPreferredSeriesImageMutation' "$series_page"
grep -Fq 'useUnsetPreferredSeriesImageMutation' "$series_page"
grep -Fq "$put_endpoint" "$series_mutations"
grep -Fq "$delete_endpoint" "$series_mutations"
grep -Fq 'imageId: selectedImage.ImageID' "$series_page"
grep -Fq 'imageType: selectedImage.ImageType' "$series_page"
grep -Fq "invalidateQueries(['image-management', 'cross-references', seriesId])" "$series_mutations"
grep -Fq "invalidateQueries(['series', seriesId, 'data'])" "$series_mutations"

if grep -Fq 'useSetPreferredImageMutation' "$series_page" \
  || grep -Fq 'useUnsetPreferredImageMutation' "$series_page" \
  || grep -Fq 'mutate(selectedImage.ID' "$series_page"; then
  printf 'error: series page still uses cross-reference preferred endpoints\n' >&2
  exit 1
fi

if grep -nE '<<<<<<<|=======|>>>>>>>' "${required_files[@]}"; then
  printf 'error: conflict markers remain in the patched WebUI\n' >&2
  exit 1
fi
