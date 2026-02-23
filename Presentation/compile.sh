#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path/to/file.tex>"
    echo "Example: $0 Presentation/TexFiles/smolVLA_Architecture.tex"
    exit 1
fi

TEXFILE="$1"
FILENAME=$(basename "$TEXFILE")
BASENAME="${FILENAME%.*}"
# Ensure the PDF directory is created relative to the script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PDF_DIR="$SCRIPT_DIR/PDF"

mkdir -p "$PDF_DIR"

echo "Compiling $FILENAME..."
# Run pdflatex, outputting all files directly to the PDF directory
pdflatex -interaction=nonstopmode -output-directory="$PDF_DIR" "$TEXFILE"

echo "Cleaning up temporary files..."
rm -f "$PDF_DIR/$BASENAME.aux"
rm -f "$PDF_DIR/$BASENAME.log"
rm -f "$PDF_DIR/$BASENAME.out"
rm -f "$PDF_DIR/$BASENAME.toc"

echo "Success! Find your PDF here: $PDF_DIR/$BASENAME.pdf"
