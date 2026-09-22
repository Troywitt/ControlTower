#!/bin/bash
# Compatibility entry point: deliberately builds only; no longer launches upstream.
set -euo pipefail
exec "$(dirname "$0")/build_private.sh"
