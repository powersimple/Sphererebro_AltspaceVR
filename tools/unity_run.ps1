# Runs work in the OPEN Unity editor without anyone at the keyboard (overnight run):
#   1. if any editor script is newer than Unity's compiled copy, bring Unity to the front so it recompiles, and wait;
#   2. write each request to Logs/sb_automation_request.txt (SphererebroAutomation.cs) and wait for it to finish.
# Usage: powershell -File tools\unity_run.ps1 build "exec SphererebroTalkShots.Run"
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Requests)
$repo = (Resolve-Path "$PSScriptRoot\..").Path; Set-Location $repo
$dll = "Library\ScriptAssemblies\Assembly-CSharp-Editor.dll"
$newest = (Get-ChildItem Assets\Editor -Recurse -Filter *.cs | Sort-Object LastWriteTime | Select-Object -Last 1).LastWriteTime
if ((Get-Item $dll).LastWriteTime -lt $newest) {
    "compiling (scripts changed at $newest)..."
    for ($try = 0; $try -lt 4 -and (Get-Item $dll).LastWriteTime -lt $newest; $try++) {
        powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\unity_focus.ps1" | Out-Null
        for ($k = 0; $k -lt 36 -and (Get-Item $dll).LastWriteTime -lt $newest; $k++) { Start-Sleep 5 }
    }
    if ((Get-Item $dll).LastWriteTime -lt $newest) { "COMPILE DID NOT HAPPEN"; exit 1 }
    "compiled at " + (Get-Item $dll).LastWriteTime
    $log = "$env:LOCALAPPDATA\Unity\Editor\Editor.log"
    $errs = Select-String -Path $log -Pattern 'error CS' | Select-Object -Last 5
    if ($errs) { $errs | ForEach-Object { $_.Line } }
    Start-Sleep 10   # the domain reload after the compile
}
foreach ($r in $Requests) {
    $n0 = (Get-Content Logs\SphererebroAutomation.txt).Count
    Set-Content Logs\sb_automation_request.txt $r -NoNewline
    $done = $false
    for ($k = 0; $k -lt 240 -and -not $done; $k++) {
        Start-Sleep 5
        $new = @(Get-Content Logs\SphererebroAutomation.txt | Select-Object -Skip $n0)
        foreach ($l in $new) { if ($l -match 'build \+ bake done|exec done|talk review shots|FAILED|REFUSED|EXEC: no') { $done = $true } }
    }
    Get-Content Logs\SphererebroAutomation.txt | Select-Object -Skip $n0
}
