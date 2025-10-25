#!/bin/bash

# package_lambda.sh
# Creates deployment ZIP for a Lambda function

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <handler_name>"
    echo "Available handlers: health, auth, init, classify, eta, plan, save, get_trip"
    exit 1
fi

HANDLER_NAME=$1
PACKAGE_DIR="lambda_packages/$HANDLER_NAME"
OUTPUT_DIR="deploy/packages"

# Validate handler name
case $HANDLER_NAME in
    health|auth|init|classify|eta|plan|save|get_trip)
        ;;
    *)
        echo "Error: Invalid handler name '$HANDLER_NAME'"
        echo "Available handlers: health, auth, init, classify, eta, plan, save, get_trip"
        exit 1
        ;;
esac

echo "Packaging Lambda function: $HANDLER_NAME"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create temporary build directory
BUILD_DIR="/tmp/lambda-build-$HANDLER_NAME"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copy handler file
if [ -f "$PACKAGE_DIR/handler.py" ]; then
    cp "$PACKAGE_DIR/handler.py" "$BUILD_DIR/"
else
    echo "Error: handler.py not found in $PACKAGE_DIR"
    exit 1
fi

# Copy shared modules
cp -r src/models "$BUILD_DIR/"
cp -r src/services "$BUILD_DIR/"
cp -r src/utils "$BUILD_DIR/"
cp src/config.py "$BUILD_DIR/"

# Install dependencies if requirements.txt exists
if [ -f "$PACKAGE_DIR/requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r "$PACKAGE_DIR/requirements.txt" -t "$BUILD_DIR" --no-deps
fi

# Create ZIP file
ZIP_FILE="$(pwd)/$OUTPUT_DIR/${HANDLER_NAME}-lambda.zip"
cd "$BUILD_DIR"
zip -r "$ZIP_FILE" . -x "*.pyc" "*/__pycache__/*" "*.dist-info/*"
cd - > /dev/null

# Clean up
rm -rf "$BUILD_DIR"

echo "Package created: $ZIP_FILE"
echo "Package size: $(du -h "$ZIP_FILE" | cut -f1)"

echo "Done!"
