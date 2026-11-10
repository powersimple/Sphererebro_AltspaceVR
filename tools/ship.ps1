# One command from an edit to the live world, in Ben's OPEN Unity editor (2026-11-09: "accelerate the build update").
#   tools\ship.ps1 -Web          script.js + index.html only (about 40 s). For cue, console and script changes.
#   tools\ship.ps1               Build World + Bake, build asset.world, upload everything (about 6 min).
#   tools\ship.ps1 -Geo          the same, after regenerating the world geometry in Blender first (adds about 1 min).
# Each step prints its time. Stops at the first failure.
param([switch]$Web, [switch]$Geo)
$repo = (Resolve-Path "$PSScriptRoot\..").Path; Set-Location $repo
$run = "$PSScriptRoot\unity_run.ps1"
$t0 = Get-Date
function Step($name) { "{0,5:0} s  {1}" -f ((Get-Date) - $t0).TotalSeconds, $name }
function Run($req) {
    $out = & powershell -ExecutionPolicy Bypass -File $run $req
    $out | Select-Object -Last 3
    if ($out -match 'FAILED|REFUSED|STOPPED|DID NOT HAPPEN') { "SHIP FAILED at '$req'"; exit 1 }
}
if ($Web) { Step "upload script"; Run web; Step "done"; exit 0 }
if ($Geo) {
    Step "Blender geometry"
    $bl = Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -Filter "Blender 5.*" |
          Sort-Object { [version]($_.Name -replace '^Blender ', '') } | Select-Object -Last 1
    $o = & (Join-Path $bl.FullName "blender.exe") -b --factory-startup --python ..\Assets\scripts\build_sphererebro.py -- ..\Assets\models Assets\_Sphererebro\Models 2>&1
    if (-not ($o -match 'SPHEREREBRO_OK')) { $o | Select-Object -Last 15; "SHIP FAILED at Blender"; exit 1 }
}
Step "Build World + Bake"; Run build
# the Builder's own Build + Confirm makes asset.world; it does not upload on its own here, so "send" follows
Step "build asset.world"
$log = Get-ChildItem *BanterBuilder.log | Sort-Object LastWriteTime | Select-Object -Last 1
$n0 = if ($log) { (Get-Content $log.FullName).Count } else { 0 }
Set-Content Logs\sb_automation_request.txt "upload" -NoNewline
$ok = $false
for ($k = 0; $k -lt 180 -and -not $ok; $k++) {
    Start-Sleep 3
    $log = Get-ChildItem *BanterBuilder.log | Sort-Object LastWriteTime | Select-Object -Last 1
    $new = @(Get-Content $log.FullName | Select-Object -Skip $n0)
    if ($new -match 'Build finished') { $ok = $true }
    if ($new -match 'Build failed|error') { $new | Select-Object -Last 5; "SHIP FAILED at asset.world"; exit 1 }
    $n0 = if ($new.Count -gt 0 -and $log.LastWriteTime -lt $t0) { 0 } else { $n0 }
}
if (-not $ok) { "SHIP FAILED: asset.world build did not finish in 9 min"; exit 1 }
Start-Sleep 3
Step "upload world"; Run send
Step "done"
