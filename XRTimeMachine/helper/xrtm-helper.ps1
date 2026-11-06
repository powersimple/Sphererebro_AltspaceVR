# XR Time Machine helper for Windows: lets the world script write real .xrtm files.
#
# The world's page can't write to disk, so while this runs it accepts the recorder's lines on
# http://localhost:47800 and appends them to Documents\AltspaceVR\XRTimeMachine\<id>.xrtm.
# It also reports the drive's free space, for the recorder's storage warnings.
# Only this PC can reach it (localhost). Stop it with Ctrl+C.
#
# Run:  powershell -ExecutionPolicy Bypass -File <path>\XRTimeMachine\helper\xrtm-helper.ps1

$ErrorActionPreference = 'Stop'
$Port = 47800
$Folder = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'AltspaceVR\XRTimeMachine'
New-Item -ItemType Directory -Force -Path $Folder | Out-Null

$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()
Write-Host "XR Time Machine helper: writing recordings to $Folder"
Write-Host "Listening on http://localhost:$Port  (Ctrl+C to stop)"

function Send($ctx, [int]$status, [string]$json) {
    $res = $ctx.Response
    $res.StatusCode = $status
    # The world page is on https://<world>.worldspace.host; allow it to call this local helper.
    $res.Headers['Access-Control-Allow-Origin'] = '*'
    $res.Headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    $res.Headers['Access-Control-Allow-Headers'] = 'Content-Type'
    $res.Headers['Access-Control-Allow-Private-Network'] = 'true'
    $res.ContentType = 'application/json'
    $bytes = [Text.Encoding]::UTF8.GetBytes($json)
    $res.OutputStream.Write($bytes, 0, $bytes.Length)
    $res.Close()
}

function SafeId([string]$id) {
    if ($id -notmatch '^[A-Za-z0-9_-]{1,120}$') { return $null }
    return $id
}

try {
    while ($listener.IsListening) {
        $ctx = $listener.GetContext()
        $req = $ctx.Request
        try {
            if ($req.HttpMethod -eq 'OPTIONS') { Send $ctx 204 ''; continue }
            $path = $req.Url.AbsolutePath
            $id = SafeId $req.QueryString['id']
            switch ($path) {
                '/xrtm/ping' {
                    # Free space on the drive the recordings go to, for the recorder's storage warnings.
                    $free = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($Folder)).AvailableFreeSpace
                    Send $ctx 200 (@{ ok = $true; folder = $Folder; free = $free; version = '0.3.0' } | ConvertTo-Json -Compress)
                }
                '/xrtm/append' {
                    if (-not $id) { Send $ctx 400 '{"ok":false,"error":"bad id"}'; break }
                    $reader = [IO.StreamReader]::new($req.InputStream, [Text.Encoding]::UTF8)
                    $text = $reader.ReadToEnd()
                    $reader.Close()
                    [IO.File]::AppendAllText((Join-Path $Folder "$id.xrtm"), $text, [Text.UTF8Encoding]::new($false))
                    Send $ctx 200 '{"ok":true}'
                }
                '/xrtm/delete' {
                    if (-not $id) { Send $ctx 400 '{"ok":false,"error":"bad id"}'; break }
                    $file = Join-Path $Folder "$id.xrtm"
                    if (Test-Path $file) { Remove-Item $file }
                    Send $ctx 200 '{"ok":true}'
                }
                '/xrtm/list' {
                    $items = Get-ChildItem $Folder -Filter *.xrtm | ForEach-Object { @{ id = $_.BaseName; bytes = $_.Length; updated = $_.LastWriteTimeUtc.ToString('o') } }
                    Send $ctx 200 (@{ ok = $true; items = @($items) } | ConvertTo-Json -Compress -Depth 4)
                }
                default { Send $ctx 404 '{"ok":false,"error":"not found"}' }
            }
        } catch {
            Write-Warning $_
            try { Send $ctx 500 '{"ok":false}' } catch { }
        }
    }
} finally {
    $listener.Stop()
}
