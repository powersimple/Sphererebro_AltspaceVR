# XR Time Machine installer, Windows: runs install.mjs (Node 22). Same flags: --off --on --status --uninstall --target.
#   powershell -ExecutionPolicy Bypass -File <path>\XRTimeMachine\install.ps1 [--off|--on|--status|--uninstall]
node (Join-Path $PSScriptRoot 'install.mjs') @args
exit $LASTEXITCODE
