using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

// Lets a Claude session build, bake and upload Sphererebro while Ben is away, in his OPEN editor, without closing Unity
// (Ben, 2026-11-07: "build and upload without me, I should not have to close Unity"). It's a watched request file:
//   Logs/sb_automation_request.txt  containing "build", "upload" or "build upload"
//     build  = Sphererebro > Build World + Bake Lighting (the same code path as the menu)
//     upload = the Creator SDK Builder window's own Build then Confirm, which builds asset.world and, with its
//              "auto upload" ticked (the default), uploads it, index.html and script.js to the selected world
// Progress goes to Logs/SphererebroAutomation.txt, and the Builder's own lines to the Editor log. Nothing runs unless the
// request file exists; it's deleted as soon as it's read, so a request runs once. Ben's rule: uploads need his OK, and
// he gives it by asking for one. The script never starts on its own.
[InitializeOnLoad]
public static class SphererebroAutomation
{
    const string RequestPath = "Logs/sb_automation_request.txt";
    const string StatusPath = "Logs/SphererebroAutomation.txt";
    static double nextPoll;
    static string pendingUpload;   // null, "open", "build", "confirm"
    static double uploadAt;
    static EditorWindow builder;

    static SphererebroAutomation() { EditorApplication.update += Poll; }

    static void Log(string s)
    {
        Directory.CreateDirectory("Logs");
        File.AppendAllText(StatusPath, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} {s}\n");
        Debug.Log("[Sphererebro automation] " + s);
    }

    static void Poll()
    {
        var now = EditorApplication.timeSinceStartup;
        if (now < nextPoll) return;
        nextPoll = now + 2.0;
        if (EditorApplication.isCompiling || EditorApplication.isUpdating || EditorApplication.isPlayingOrWillChangePlaymode) return;
        if (pendingUpload != null) { StepUpload(now); return; }
        if (!File.Exists(RequestPath)) return;
        string what;
        try { what = File.ReadAllText(RequestPath).Trim().ToLowerInvariant(); File.Delete(RequestPath); }
        catch (Exception e) { Log("couldn't read the request: " + e.Message); return; }
        Log("request: " + what);
        try
        {
            if (what.Contains("build"))
            {
                if (!SphererebroBuilder.BuildForAutomation(true)) { Log("BUILD REFUSED (the builder's scripts were newer than Unity's compiled copy)"); return; }
                Log("build + bake done (Logs/SphererebroBuilder.txt)");
            }
            if (what.Contains("upload")) { pendingUpload = "open"; uploadAt = now; }
        }
        catch (Exception e) { Log("FAILED: " + e); pendingUpload = null; }
    }

    // the Builder window's own path, step by step, a couple of seconds apart (its UI must exist before Build)
    static void StepUpload(double now)
    {
        if (now < uploadAt) return;
        try
        {
            var type = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("BuilderWindow", false)).FirstOrDefault(t => t != null);
            if (type == null) { Log("UPLOAD FAILED: the Creator SDK's BuilderWindow wasn't found"); pendingUpload = null; return; }
            const BindingFlags F = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public;
            switch (pendingUpload)
            {
                case "open":
                    builder = EditorWindow.GetWindow(type);
                    Log("Builder window open");
                    pendingUpload = "build"; uploadAt = now + 4; return;
                case "build":
                    if (builder == null) builder = EditorWindow.GetWindow(type);
                    var build = type.GetMethod("BuildAssetBundles", F);
                    if (build == null) { Log("UPLOAD FAILED: BuilderWindow.BuildAssetBundles not found (SDK changed?)"); pendingUpload = null; return; }
                    build.Invoke(builder, null);   // saves, runs the checklist, shows the confirmation
                    pendingUpload = "confirm"; uploadAt = now + 3; return;
                case "confirm":
                    var cb = type.GetField("confirmCallback", F)?.GetValue(builder) as Action;
                    if (cb == null) { Log("UPLOAD STOPPED: no confirmation pending: the Builder's checklist or scene check stopped it (see its status line)"); pendingUpload = null; return; }
                    Log("confirming: the Builder builds asset.world, then uploads (its 'auto upload' setting)");
                    pendingUpload = null;
                    cb();   // the Builder hides its confirm panel itself when clicked; here it simply proceeds
                    return;
            }
        }
        catch (Exception e) { Log("UPLOAD FAILED: " + e); pendingUpload = null; }
    }
}
