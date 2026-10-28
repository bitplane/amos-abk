#!/bin/bash

set -e -o pipefail

source .venv/bin/activate

VERSION=$(grep -E '^version[[:space:]]*=' pyproject.toml | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/')
TAG_NAME=$(git describe --exact-match --tags HEAD)

if [[ "$VERSION" != "$TAG_NAME" ]]; then
    echo "Tag and version do not match!"
    echo "Tag: $TAG_NAME, Version: $VERSION"
    exit 1
fi

if [ -z "$PYPI_TOKEN" ]; then
  echo "PYPI_TOKEN is not set. Can't authenticate to upload"
  exit 1
fi

# Keep release builds separate from previous distributions. Use the project's
# dist directory rather than /tmp, which may be a small RAM-backed filesystem.
mkdir -p dist
release_dir=$(mktemp -d dist/release.XXXXXXXX)
trap 'rm -rf -- "$release_dir"' EXIT

python3 -m build --outdir "$release_dir" .
python3 -m twine check "$release_dir"/*
python3 -m twine upload "$release_dir"/* --user=__token__ --password="$PYPI_TOKEN"
