#!/usr/bin/env bash
# Build and validate distribution artifacts for PyPI.
set -euo pipefail

cd "$(dirname "$0")/.."

python -m pip install -q --upgrade build twine
rm -rf dist build *.egg-info src/*.egg-info
python -m build
python -m twine check dist/*
echo
echo "Artifacts ready in dist/:"
ls -la dist/
echo
echo "Next (manual upload):"
echo "  # TestPyPI:"
echo "  twine upload --repository testpypi dist/*"
echo "  # PyPI:"
echo "  twine upload dist/*"
echo
echo "Or tag a release for GitHub Actions trusted publishing:"
echo "  git tag v0.1.0 && git push origin v0.1.0"
