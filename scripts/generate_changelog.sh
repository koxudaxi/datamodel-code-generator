#!/bin/bash
# Generate CHANGELOG.md from all GitHub Releases
# Usage: ./scripts/generate_changelog.sh > CHANGELOG.md
# Note: --limit 500 may need to be increased if releases exceed 500

set -euo pipefail

REPO="koxudaxi/datamodel-code-generator"

echo "# Changelog"
echo ""
echo "All notable changes to this project are documented in this file."
echo "This changelog is automatically generated from GitHub Releases."
echo ""
echo "---"
echo ""

# Get all releases and process them
gh release list --repo "$REPO" --limit 500 --json tagName --jq '.[].tagName' | while read -r tag; do
    # Get release details (use // "" to handle null body)
    DATE=$(gh release view "$tag" --repo "$REPO" --json publishedAt --jq '.publishedAt | split("T")[0]')
    BODY=$(gh release view "$tag" --repo "$REPO" --json body --jq '.body // ""')

    echo "## [$tag](https://github.com/$REPO/releases/tag/$tag) - $DATE"
    echo ""
    printf '%s\n' "$BODY"
    echo ""
    echo "---"
    echo ""
done
