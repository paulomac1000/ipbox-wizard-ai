#!/usr/bin/env bash
set -euo pipefail
ROOT="$(realpath "${1:-.}")"
OUTPUT="$(realpath -m "${2:-/tmp/ipbox-wizard-ai.md}")"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

printf '# Repository dump: ipbox-wizard-ai\n\n' > "$TMP"
while IFS= read -r -d '' file; do
  rel="${file#$ROOT/}"
  [[ "$file" == "$OUTPUT" ]] && continue
  case "$rel" in
    .git/*|.venv/*|venv/*|input/*|reports/*|tmp/*|.omo/*|__pycache__/*|*/__pycache__/*|\
    .pytest_cache/*|.ruff_cache/*|tests/llm/vcr/cassettes/*|.env|.env.*|*.pyc|*.pem|*.key)
      continue ;;
  esac
  case "$rel" in
    *.py|*.md|*.txt|*.toml|*.yaml|*.yml|*.json|*.sh|*.example|Makefile|LICENSE) ;;
    *) continue ;;
  esac
  grep -Iq . "$file" || continue
  max=2
  while IFS= read -r line; do
    if [[ "$line" =~ ^(\`+) ]]; then
      n=${#BASH_REMATCH[1]}; (( n > max )) && max=$n
    fi
  done < "$file"
  fence="$(printf '%*s' "$((max + 1))" '' | tr ' ' '`')"
  printf '## `%s`\n\n%s\n' "$rel" "$fence" >> "$TMP"
  cat "$file" >> "$TMP"
  printf '\n%s\n\n' "$fence" >> "$TMP"
done < <(find "$ROOT" -type f -print0 | sort -z)

if grep -Eqi "(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|Bearer [A-Za-z0-9._-]{20,}|sk-[A-Za-z0-9_-]{20,}|OPENROUTER_API_KEY[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9._-]{20,})" "$TMP"; then
  echo 'Potential secret detected; refusing to write dump' >&2
  exit 1
fi
mkdir -p "$(dirname "$OUTPUT")"
mv "$TMP" "$OUTPUT"
trap - EXIT
printf 'Wrote %s\n' "$OUTPUT"
