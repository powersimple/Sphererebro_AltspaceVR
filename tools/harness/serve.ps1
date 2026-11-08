# The show harness's local server (no Node/Python needed). Serves the Sphererebro folder (this repo and the sibling
# ..\Assets) on http://localhost:8766/ and accepts POST /save?path=review/... (PNG or text from the harness) into this repo.
# Open http://localhost:8766/Sphererebro_AltspaceVR/tools/harness/show.html . Ctrl+C to stop.
param([int]$Port = 8766)
$Repo = (Resolve-Path "$PSScriptRoot\..\..").Path
$Root = (Resolve-Path "$Repo\..").Path
$l = New-Object System.Net.HttpListener; $l.Prefixes.Add("http://localhost:$Port/"); $l.Start()
"serving $Root on http://localhost:$Port/  (saves into $Repo\review)"
$types = @{ ".html" = "text/html"; ".js" = "text/javascript"; ".mjs" = "text/javascript"; ".css" = "text/css"; ".png" = "image/png";
            ".jpg" = "image/jpeg"; ".json" = "application/json"; ".glb" = "model/gltf-binary"; ".wav" = "audio/wav"; ".mp4" = "video/mp4" }
while ($l.IsListening) {
    $c = $l.GetContext()
    try {
        if ($c.Request.HttpMethod -eq "POST" -and $c.Request.Url.AbsolutePath -eq "/save") {
            $rel = $c.Request.QueryString["path"]
            $dst = [IO.Path]::GetFullPath((Join-Path $Repo $rel))
            if (-not $dst.StartsWith((Join-Path $Repo "review"))) { $c.Response.StatusCode = 403 }
            else {
                New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
                $ms = New-Object IO.MemoryStream; $c.Request.InputStream.CopyTo($ms); $bytes = $ms.ToArray()
                $txt = [Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(30, $bytes.Length))
                if ($txt.StartsWith("data:image/png;base64,")) { $bytes = [Convert]::FromBase64String([Text.Encoding]::ASCII.GetString($bytes).Substring(22)) }
                [IO.File]::WriteAllBytes($dst, $bytes); "saved $rel ($($bytes.Length) bytes)"
            }
        } else {
            $p = Join-Path $Root ([Uri]::UnescapeDataString($c.Request.Url.AbsolutePath.TrimStart('/')))
            if ((Test-Path $p -PathType Leaf) -and ([IO.Path]::GetFullPath($p).StartsWith($Root))) {
                $b = [IO.File]::ReadAllBytes($p); $ct = $types[[IO.Path]::GetExtension($p).ToLower()]
                if ($ct) { $c.Response.ContentType = $ct }
                $c.Response.Headers.Add("Cache-Control", "no-store")
                $c.Response.OutputStream.Write($b, 0, $b.Length)
            } else { $c.Response.StatusCode = 404 }
        }
    } catch { $c.Response.StatusCode = 500; "error: $_" }
    $c.Response.Close()
}
