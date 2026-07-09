#!/bin/bash
set -euo pipefail

INPUT_PATH="${1:?Usage: $0 <path>}"
OUTPUT_DIR="${2:-.}"
SCRIPT_NAME="dump-to-md.sh"
TEXT_EXTS="\.(py|json|md|txt|tsv|sh|log|yaml|yml|cfg|conf|toml|ini|xml|html|css|js|svg|tex|r|R|c|cpp|h|rb|go|rs|java|php|pl|pm|lua|vim|ps1|bat|env|sample|example|jinja|jinja2|properties|gradle|makefile|dockerfile|Dockerfile|gitignore|gitkeep|editorconfig)"

if [ ! -d "$INPUT_PATH" ]; then
    echo "Error: not a directory" >&2
    exit 1
fi

ABS_PATH=$(realpath "$INPUT_PATH")
FOLDER_NAME=$(basename "$ABS_PATH")
OUTPUT_FILE="${OUTPUT_DIR}/${FOLDER_NAME}.md"
OUTPUT_NAME=$(basename "$OUTPUT_FILE")

echo "# $FOLDER_NAME" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

total=0
skipped_nontext=0
skipped_excluded=0

# Find all files, then filter by extension and exclusion paths
while IFS= read -r -d '' f; do
    rel="${f#$ABS_PATH/}"
    [ -z "$rel" ] && continue

    # Skip script itself and output file
    if [ "$rel" = "$SCRIPT_NAME" ] || [ "$rel" = "$OUTPUT_NAME" ]; then
        continue
    fi

    # Skip real .env files with secrets
    case "$rel" in
        .env|*/.env)
            skipped_excluded=$((skipped_excluded+1))
            continue
            ;;
    esac

    # Skip known binary-heavy / non-project directories
    case "$rel" in
        tools/multiqc-venv/*|tools/fastqc/FastQC/*|tools/fastqc/*.zip|tools/downloads/*|tools/seqkit/seqkit)
            skipped_excluded=$((skipped_excluded+1))
            continue
            ;;
    esac

    # Only include text file extensions
    if ! echo "$rel" | grep -qiE "${TEXT_EXTS}$" 2>/dev/null; then
        skipped_nontext=$((skipped_nontext+1))
        continue
    fi

    total=$((total+1))
    echo "## $rel" >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    cat "$f" >> "$OUTPUT_FILE"
    echo >> "$OUTPUT_FILE"
    echo '```' >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
done < <(find "$ABS_PATH" -type f -print0 2>/dev/null)

echo "--- Statistics ---" >> "$OUTPUT_FILE"
echo "- Total text files dumped: $total" >> "$OUTPUT_FILE"
echo "- Skipped (non-text): $skipped_nontext" >> "$OUTPUT_FILE"
echo "- Skipped (excluded dirs): $skipped_excluded" >> "$OUTPUT_FILE"

echo "Done: $OUTPUT_FILE ($total text files, $skipped_nontext non-text skipped, $skipped_excluded excluded dirs skipped)"
