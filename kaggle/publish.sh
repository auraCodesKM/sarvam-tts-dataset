#!/usr/bin/env bash
# Stage and publish the dataset to Kaggle.
# Requires ~/.kaggle/kaggle.json (Kaggle -> Account -> API -> Create New Token).
set -euo pipefail

cd "$(dirname "$0")/.."
STAGE=kaggle/upload

rm -rf "$STAGE"
mkdir -p "$STAGE/clips"
cp data/manifest.csv "$STAGE/manifest.csv"
cp data/clips/*.wav "$STAGE/clips/"
cp kaggle/dataset-metadata.json "$STAGE/dataset-metadata.json"

echo "Staged $(ls "$STAGE/clips" | wc -l) clips + manifest.csv in $STAGE"

if [ "${1:-}" = "create" ]; then
  kaggle datasets create -p "$STAGE" --dir-mode zip
elif [ "${1:-}" = "update" ]; then
  kaggle datasets version -p "$STAGE" --dir-mode zip -m "${2:-dataset update}"
else
  echo "Usage: $0 create   (first publish)"
  echo "       $0 update \"message\"   (subsequent updates)"
  echo "After first publish, paste the KAGGLE_DESCRIPTION.md content into the"
  echo "dataset's description box on kaggle.com (the API doesn't set it)."
fi
