# Regenerates the talk after an edit to Assets/_Sphererebro/Config/talk_show.json (cue order, text, video) or to
# tools/talk/choreo.py (motion): the timeline JSON, script.js's show block, and XR Time Machine in script.js.
#   cue order / video / which elements a cue brings on or off: script.js only (upload HTML + JS; no scene build)
#   text, motion, new elements: also Sphererebro > Build World (+ Bake) in Unity, then the Builder's build and upload
# Add -Assets to rebuild every Blender asset first; -Sounds to resynthesise the sounds; -Cards for the timeline cards.
param([switch]$Assets, [switch]$Sounds, [switch]$Cards)
$repo = (Resolve-Path "$PSScriptRoot\..\..").Path; Set-Location $repo
# Blender's bundled Python from the newest Blender 5.x installed (5.2 on Yoda-VIII, 5.1 on Yoda-IX).
$bl = Get-ChildItem "C:\Program Files\Blender Foundation" -Directory -Filter "Blender 5.*" |
      Sort-Object { [version]($_.Name -replace '^Blender ', '') } | Select-Object -Last 1
$py = Join-Path $bl.FullName "$($bl.Name -replace '^Blender ', '')\python\bin\python.exe"
"Blender: $($bl.Name)"
if ($Assets) { & $py tools\blender\build_all.py; if ($LASTEXITCODE) { "asset build FAILED"; exit 1 } }
if ($Cards) { & $py tools\talk\make_cards.py }
if ($Sounds) { & $py tools\talk\sounds.py }
& $py tools\talk\choreo.py; if ($LASTEXITCODE) { "choreo FAILED"; exit 1 }
& powershell -ExecutionPolicy Bypass -File ..\Assets\scripts\install_xrtm.ps1
"done. Test: tools/harness/serve.ps1, then http://localhost:8766/Sphererebro_AltspaceVR/tools/harness/show_test.html and show.html"
