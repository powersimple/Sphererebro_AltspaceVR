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
            // "exec Class.Method": run a static editor method (review shots, checks), e.g. exec SphererebroTalkShots.Run
            if (what.StartsWith("exec "))
            {
                var spec = File.Exists(RequestPath + ".exec") ? File.ReadAllText(RequestPath + ".exec").Trim() : what.Substring(5).Trim();
                var dot = spec.LastIndexOf('.');
                var type = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType(spec.Substring(0, dot), false, true)).FirstOrDefault(t => t != null);
                var m = type?.GetMethod(spec.Substring(dot + 1), BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.IgnoreCase);
                if (m == null) { Log("EXEC: no static method " + spec); return; }
                Log("exec " + spec); m.Invoke(null, null); Log("exec done: " + spec);
                return;
            }
            // "web": script.js and index.html only (the Builder's own "Upload HTML + JS"); no scene build, asset.world untouched
            if (what == "web") { pendingUpload = "web-open"; uploadAt = now; return; }
            // "send": upload what is already built (asset.world + index.html + script.js), the Builder's Upload Everything
            if (what == "send") { pendingUpload = "send-open"; uploadAt = now; return; }
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
                case "web-open":
                case "send-open":
                    builder = EditorWindow.GetWindow(type);
                    Log("Builder window open (web only)");
                    pendingUpload = pendingUpload == "send-open" ? "send-go" : "web-go"; uploadAt = now + 6; return;
                case "web-go":
                case "send-go":
                {
                    var all = pendingUpload == "send-go";
                    pendingUpload = null;
                    if (builder == null) builder = EditorWindow.GetWindow(type);
                    var web = type.GetMethod(all ? "UploadEverything" : "UploadWebOnly", F);
                    var world = type.GetField("selectedWorld", F)?.GetValue(builder);
                    if (web == null) { Log("WEB UPLOAD FAILED: BuilderWindow.UploadWebOnly not found (SDK changed?)"); return; }
                    if (world == null) { Log("WEB UPLOAD FAILED: no world is selected in the Builder window"); return; }
                    var win = builder;
                    Action done = () =>
                    {
                        var bad = type.GetField("uploadHadFailure", F)?.GetValue(win);
                        Log(bad is bool b2 && b2 ? "WEB UPLOAD FAILED: the Builder reported a failure (see its status line)" : (all ? "web upload done: asset.world, index.html and script.js" : "web upload done: index.html and script.js"));
                    };
                    var routine = (System.Collections.IEnumerator)web.Invoke(builder, new object[] { done });
                    var util = AppDomain.CurrentDomain.GetAssemblies().Select(a => a.GetType("Unity.EditorCoroutines.Editor.EditorCoroutineUtility", false)).FirstOrDefault(t => t != null);
                    var startCo = util?.GetMethod("StartCoroutine", new[] { typeof(System.Collections.IEnumerator), typeof(object) });
                    if (startCo == null) { Log("WEB UPLOAD FAILED: EditorCoroutineUtility not found"); return; }
                    Log("uploading index.html and script.js");
                    startCo.Invoke(null, new object[] { routine, builder });
                    return;
                }
                case "build":
                    if (builder == null) builder = EditorWindow.GetWindow(type);
                    var build = type.GetMethod("BuildAssetBundles", F);
                    if (build == null) { Log("UPLOAD FAILED: BuilderWindow.BuildAssetBundles not found (SDK changed?)"); pendingUpload = null; return; }
                    // save first: with the scene unsaved the Builder puts up a modal "save the scene?" and everything waits (2026-11-09)
                    UnityEditor.SceneManagement.EditorSceneManager.SaveOpenScenes();
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
