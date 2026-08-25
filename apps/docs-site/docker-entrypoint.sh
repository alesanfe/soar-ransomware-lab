#!/bin/sh
# Entrypoint for Docusaurus docs-site container.
# Syncs chart images from /opt/charts into the docs directory and creates
# placeholders for any missing images so the build never fails.

set -e

CHARTS_SRC="/opt/charts"
CHARTS_DST="/opt/docusaurus/docs/reports/e2e/charts"

# Ensure target directory exists
mkdir -p "$CHARTS_DST"

# List all chart images referenced in the e2e_report.md
REPORT_FILE="/opt/docusaurus/docs/reports/e2e/e2e_report.md"
if [ -f "$REPORT_FILE" ]; then
    # Extract image filenames from the markdown (./charts/<name>.png)
    images=$(grep -oE '\./charts/[A-Za-z0-9_.-]+\.(png|svg|jpg)' "$REPORT_FILE" | sed 's|\./charts/||' | sort -u)
    for img in $images; do
        dst="$CHARTS_DST/$img"
        src="$CHARTS_SRC/$img"
        if [ -f "$src" ]; then
            cp -f "$src" "$dst"
            echo "[entrypoint] Copied chart: $img"
        elif [ -f "$dst" ]; then
            echo "[entrypoint] Chart already present: $img"
        else
            # Create empty placeholder PNG (1x1 transparent pixel)
            printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\xfe\x02\xfe\xa1Yz\xc6\x00\x00\x00\x00IEND\xaeB`\x82' > "$dst"
            echo "[entrypoint] Created placeholder for missing chart: $img"
        fi
    done
fi

# Also check operations images — copy from baked /opt/ops-images or create placeholders
# Images in operations/intro.md are referenced as assets/images/... (relative to the markdown dir)
# So they resolve to /opt/docusaurus/docs/operations/assets/images/...
OPS_IMG_SRC="/opt/ops-images"
OPS_FILE="/opt/docusaurus/docs/operations/intro.md"
OPS_DIR="/opt/docusaurus/docs/operations"
if [ -f "$OPS_FILE" ]; then
    ops_images=$(grep -oE 'assets/images/[A-Za-z0-9_/]+\.(png|svg|jpg)' "$OPS_FILE" | sort -u)
    for img_path in $ops_images; do
        full_path="$OPS_DIR/$img_path"
        rel_path="${img_path#assets/images/}"
        src_path="$OPS_IMG_SRC/$rel_path"
        if [ -f "$full_path" ]; then
            echo "[entrypoint] Operations image already present: $img_path"
        elif [ -f "$src_path" ]; then
            mkdir -p "$(dirname "$full_path")"
            cp -f "$src_path" "$full_path"
            echo "[entrypoint] Copied operations image: $img_path"
        else
            mkdir -p "$(dirname "$full_path")"
            printf '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\xfe\x02\xfe\xa1Yz\xc6\x00\x00\x00\x00IEND\xaeB`\x82' > "$full_path"
            echo "[entrypoint] Created placeholder for missing image: $img_path"
        fi
    done
fi

echo "[entrypoint] Docs preparation complete. Starting Docusaurus..."

# Execute the main command (npm start)
exec "$@"
