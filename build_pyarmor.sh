#!/bin/bash
# PyArmor build script — protection layer
echo "═══ GOJI PYARMOR BUILD ═══"
pip install pyarmor

echo "[1/3] cleaning old build"
rm -rf dist build
mkdir -p dist

echo "[2/3] obfuscating client"
pyarmor gen --output dist --recursive goji_client.py

echo "[3/3] done"
ls -la dist/
echo ""
echo "✓ output: dist/goji_client.py + dist/pyarmor_runtime_*/"
echo "  distribute these 2 to customers"