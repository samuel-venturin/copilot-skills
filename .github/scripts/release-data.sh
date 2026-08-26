#!/usr/bin/env bash
set -euo pipefail

SEMVER_PATTERN='v[0-9]*.[0-9]*.[0-9]*'

# Build tag list sorted by creation date (most recently created tag first).
# Intentional: avoids picking accidental high-number tags (e.g. v11.x) over
# real ones (e.g. v1.65.x) that were created later.
all_tags=()
while IFS= read -r line; do
  [[ -n "$line" ]] && all_tags+=("$line")
done < <(git for-each-ref --sort=-creatordate --format='%(refname:short)' "refs/tags/$SEMVER_PATTERN")

# Allow the Python orchestrator to override tag detection via env vars.
# When set, the script skips its own detection and uses these values directly.
if [[ -n "${RELEASE_LAST_TAG:-}" ]]; then
  last_tag="$RELEASE_LAST_TAG"
  previous_tag="${RELEASE_PREVIOUS_TAG:-}"
else
  last_tag="${all_tags[0]:-}"
  previous_tag="${all_tags[1]:-}"
fi

if [[ -z "$last_tag" ]]; then
  echo "ERROR=No semantic tags found. Create a tag first (format v#.#.#)."
  exit 1
fi

if [[ -n "$previous_tag" ]]; then
  range="${previous_tag}..${last_tag}"
else
  range="$last_tag"
fi

commits_raw="$(git log --pretty=format:'%h|%an|%aI|%s' "$range")"

commit_count=0
author_count=0
file_count=0
first_commit_at=""
last_commit_at=""
time_window_hours=0
complexity_score=0
complexity_level="LOW"
complexity_bombs="💣"

if [[ -n "$commits_raw" ]]; then
  commit_count="$(printf '%s\n' "$commits_raw" | grep -c . || true)"
  author_count="$(printf '%s\n' "$commits_raw" | cut -d'|' -f2 | sort -u | grep -c . || true)"

  files_raw="$(git diff --name-only "$range")"
  if [[ -n "$files_raw" ]]; then
    file_count="$(printf '%s\n' "$files_raw" | grep -c . || true)"
  fi

  first_commit_at="$(git log --reverse --format='%aI' -1 "$range")"
  last_commit_at="$(git log --format='%aI' -1 "$range")"

  if [[ -n "$first_commit_at" && -n "$last_commit_at" ]]; then
    start_epoch="$(date -d "$first_commit_at" +%s)"
    end_epoch="$(date -d "$last_commit_at" +%s)"
    if [[ "$end_epoch" -ge "$start_epoch" ]]; then
      time_window_hours="$(((end_epoch - start_epoch) / 3600))"
    fi
  fi
fi

# Complexity score heuristic (0-10)
complexity_score=$(( (commit_count * 2 + file_count + author_count) / 4 ))
if [[ "$complexity_score" -gt 10 ]]; then
  complexity_score=10
fi

if [[ "$complexity_score" -le 2 ]]; then
  complexity_level="LOW"
  complexity_bombs="💣"
elif [[ "$complexity_score" -le 4 ]]; then
  complexity_level="MODERATE"
  complexity_bombs="💣💣"
elif [[ "$complexity_score" -le 6 ]]; then
  complexity_level="HIGH"
  complexity_bombs="💣💣💣"
elif [[ "$complexity_score" -le 8 ]]; then
  complexity_level="VERY_HIGH"
  complexity_bombs="💣💣💣💣"
else
  complexity_level="EXTREME"
  complexity_bombs="💣💣💣💣💣"
fi

echo "LAST_TAG=$last_tag"
echo "PREVIOUS_TAG=${previous_tag:-none}"
echo "RANGE=$range"
echo "COMMIT_COUNT=$commit_count"
echo "AUTHOR_COUNT=$author_count"
echo "FILE_COUNT=$file_count"
echo "FIRST_COMMIT_AT=${first_commit_at:-n/a}"
echo "LAST_COMMIT_AT=${last_commit_at:-n/a}"
echo "TIME_WINDOW_HOURS=$time_window_hours"
echo "COMPLEXITY_SCORE=$complexity_score"
echo "COMPLEXITY_LEVEL=$complexity_level"
echo "COMPLEXITY_BOMBS=$complexity_bombs"

echo "AUTHORS_START"
if [[ -n "$commits_raw" ]]; then
  printf '%s\n' "$commits_raw" | cut -d'|' -f2 | sort -u | sed 's/^/- /'
else
  echo "- n/a"
fi
echo "AUTHORS_END"

echo "COMMITS_START"
if [[ -n "$commits_raw" ]]; then
  printf '%s\n' "$commits_raw" | while IFS='|' read -r hash author date subject; do
    if [[ -n "$hash" ]]; then
      echo "- ${hash} ${subject} (${author})"
    fi
  done
else
  echo "- n/a"
fi
echo "COMMITS_END"

echo "FILES_START"
if [[ -n "${files_raw:-}" ]]; then
  printf '%s\n' "$files_raw" | sed 's/^/- /'
else
  echo "- n/a"
fi
echo "FILES_END"
