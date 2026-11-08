# Brings the open Unity editor (this project) to the front, so its Auto Refresh imports and compiles changed scripts and
# assets while nobody is at the keyboard (Unity refreshes on focus gain). The Alt tap lets SetForegroundWindow work from a
# background process. Used by the overnight run; harmless otherwise.
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern void keybd_event(byte k, byte s, uint f, UIntPtr e);
}
"@
$u = Get-Process Unity -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -match "Sphererebro" } | Select-Object -First 1
if (-not $u) { "no Unity window for Sphererebro"; exit 1 }
[W]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero); [W]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
# lose focus first (Unity refreshes on focus GAIN): minimise, then restore
[W]::ShowWindow($u.MainWindowHandle, 6) | Out-Null; Start-Sleep -Milliseconds 600
[W]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero); [W]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
[W]::ShowWindow($u.MainWindowHandle, 9) | Out-Null
"focused: " + [W]::SetForegroundWindow($u.MainWindowHandle) + "  (" + $u.MainWindowTitle + ")"
