#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ML_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ARTIFACT_DIR="$ML_DIR/artifacts"
BUILD_DIR="$SCRIPT_DIR/lambda_build"
PKG_DIR="$BUILD_DIR/package"
ZIP_PATH="$SCRIPT_DIR/fraud_lambda.zip"

echo "== Cleaning old build =="
rm -rf "$BUILD_DIR" "$ZIP_PATH"
mkdir -p "$PKG_DIR/artifacts"

echo "== Training/exporting model =="
python3 -m pip install numpy==1.26.4 scikit-learn==1.4.2
python3 "$SCRIPT_DIR/train_and_package.py"

echo "== Copying files =="
cp "$SCRIPT_DIR/lambda_function.py" "$PKG_DIR/"
cp "$ARTIFACT_DIR/fraud_forest.json" "$PKG_DIR/artifacts/"
cp "$ARTIFACT_DIR/fraud_cdf.json" "$PKG_DIR/artifacts/"
cp "$ARTIFACT_DIR/feature_metadata.json" "$PKG_DIR/artifacts/"

echo "== Creating zip =="
(
  cd "$PKG_DIR"
  zip -r -9 "$ZIP_PATH" .
)

echo "== Done =="
ls -lh "$ZIP_PATH"