#!/usr/bin/env bash
set -euo pipefail

if [[ ! -e build-cov ]]; then
    meson setup build-cov
fi
cd build-cov
ninja
ninja test
ninja coverage
cd meson-logs/coveragereport
python -m http.server 9999
