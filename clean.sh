#!/bin/bash
echo "Cleaning build artifacts..."

# Remove Cython generated C files (be careful not to delete the handwritten ones!)
rm -f src/super_slurpy/core.c

# Remove compiled shared objects
find . -name "*.so" -type f -delete
find . -name "*.pyd" -type f -delete

# Remove Python/uv build caches
rm -rf .venv/
rm -rf *.egg-info/
rm -rf src/*/*.egg-info/

echo "Clean complete. You can now run 'uv sync' for a fresh build."