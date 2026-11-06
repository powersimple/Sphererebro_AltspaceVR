#!/bin/bash
# XR Time Machine installer, macOS/Linux: runs install.mjs (Node 22). Same flags: --off --on --status --uninstall --target.
exec node "$(cd "$(dirname "$0")" && pwd)/install.mjs" "$@"
