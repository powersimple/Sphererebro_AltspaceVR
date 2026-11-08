using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using J = SphererebroTalkJson;

// The talk's review: for every cue, the scene as the presenter leaves it (every live element in its final, held pose),
// rendered from the centre of the front row (review/cues/NN_<cue>.png) and from behind the audience (..._wide.png),
// plus the visible triangle and draw-call count of the talk in each cue (review/PERFORMANCE.md). Menu: Sphererebro >
// Talk > Review Shots, or the automation request "exec SphererebroTalkShots.Run". The scene is reopened from disk at
// the end, so nothing here is saved.
public static class SphererebroTalkShots
{
    const string ScenePath = "Assets/_Sphererebro/Scenes/Sphererebro.unity";

    [MenuItem("Sphererebro/Talk/Review Shots")]
    public static void Run()
    {
        var talk = GameObject.Find("Talk");
        if (talk == null) { EditorSceneManager.OpenScene(ScenePath); talk = GameObject.Find("Talk"); }
        if (talk == null) { Debug.LogError("[Talk] no Talk root in the scene: build first"); return; }
        ShaderUtil.allowAsyncCompilation = false;
        var tl = J.O(J.Parse(File.ReadAllText("Assets/_Sphererebro/Config/talk_timeline.json")));
        var cues = J.L(tl["cues"]).Select(J.O).ToList();
        var els = J.O(tl["elements"]);
        talk.transform.position = Vector3.zero;
        // the world as the script leaves it at load: the 8K skybox (every dome shell off), the IPN cube hidden
        foreach (var n in new[] { "Sphere_Screen", "Sphere_Shell_Glow", "Sphere_Shell_Inner", "IPN_Cube", "Sphere_Load_Ring_EMIT", "Sphere_Lattice" })
        { var g = GameObject.Find(n); if (g) g.SetActive(false); }
        var twins = new Dictionary<string, GameObject>();
        foreach (Transform t in talk.transform) twins[t.name] = t.gameObject;
        void SetAll(bool on) { foreach (var g in twins.Values) g.SetActive(on); }
        var outDir = Path.GetFullPath("review/cues"); Directory.CreateDirectory(outDir);
        foreach (var f in Directory.GetFiles(outDir, "*.png")) File.Delete(f);
        var cam = new GameObject("TalkReviewCam").AddComponent<Camera>();
        cam.nearClipPlane = 0.1f; cam.farClipPlane = 2000f;
        var rt = new RenderTexture(1920, 1080, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        cam.targetTexture = rt;
        var perf = new StringBuilder();
        perf.AppendLine("# Talk performance, per cue (Unity editor count of what is switched on)");
        perf.AppendLine();
        perf.AppendLine($"Measured {DateTime.Now:yyyy-MM-dd HH:mm} by SphererebroTalkShots (Unity editor, held pose of each cue).");
        perf.AppendLine("Triangles and draw calls are the TALK's active renderers (each submesh = one draw call; the SRP batcher makes repeats cheap).");
        perf.AppendLine("The world's own geometry visible from the seats adds about " + WorldBaseline() + ". Budget (Quest): < 300,000 visible triangles, < 150 draw calls.");
        perf.AppendLine("Frame rate cannot be measured in the editor; see review/REVIEW.md for the browser harness and what needs a headset.");
        perf.AppendLine();
        perf.AppendLine("| # | Cue | Name | Talk triangles | Draw calls | Lights | Over budget? |");
        perf.AppendLine("|---|---|---|---:|---:|---:|---|");
        var videoTex = new Dictionary<string, Texture2D>();
        for (int i = 1; i <= cues.Count; i++)
        {
            SetAll(false);
            var live = new HashSet<string>();
            for (int k = 0; k < i; k++) { foreach (var e in J.L(cues[k]["off"])) live.Remove((string)e); foreach (var e in J.L(cues[k]["on"])) live.Add((string)e); }
            foreach (var e in live) if (twins.TryGetValue($"Talk_{e}_Hold", out var h)) h.SetActive(true);
            // video: the last cue at or before i that says something
            object video = null;
            for (int k = 0; k < i; k++) { var v = J.G(cues[k], "video"); if (v is string s && s == "stop") video = null; else if (v != null) video = v; }
            if (video is Dictionary<string, object> vd)
            {
                var name = $"Talk_Video_{vd["surface"]}_{J.S(J.G(vd, "layout"), "mono")}";
                if (twins.TryGetValue(name, out var vo))
                {
                    vo.SetActive(true);
                    var clip = J.S(vd["clip"]);
                    var still = Path.Combine("talk/gen", "still_" + clip.Replace('/', '_').Replace(".mp4", ".png"));
                    if (File.Exists(still))
                    {
                        if (!videoTex.TryGetValue(still, out var tex)) { tex = new Texture2D(2, 2); tex.LoadImage(File.ReadAllBytes(still)); videoTex[still] = tex; }
                        vo.GetComponent<MeshRenderer>().sharedMaterial.SetTexture("_BaseMap", tex);
                    }
                }
            }
            var c = cues[i - 1];
            var id = J.S(c["id"]);
            var file = $"{i:00}_{id}";
            Shot(cam, rt, Path.Combine(outDir, file + ".png"), new Vector3(0, -1.15f, -40.1f), new Vector3(0, 1.0f, 0), 95f);
            Shot(cam, rt, Path.Combine(outDir, file + "_wide.png"), new Vector3(0, 9f, -49.0f), new Vector3(0, 0f, 0f), 85f);
            // counts
            int tris = 0, calls = 0, lights = 0;
            foreach (var r in talk.GetComponentsInChildren<Renderer>(false))
            {
                if (!r.enabled) continue;
                if (r is MeshRenderer) { var mf = r.GetComponent<MeshFilter>(); if (mf && mf.sharedMesh) { for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tris += (int)mf.sharedMesh.GetIndexCount(s) / 3; calls += mf.sharedMesh.subMeshCount; } }
                else calls += 1;
            }
            lights = talk.GetComponentsInChildren<Light>(false).Count(l => l.enabled && l.intensity > 0);
            bool over = tris > 300000 || calls > 150;
            perf.AppendLine($"| {i} | {id} | {J.S(c["name"])} | {tris:N0} | {calls} | {lights} | {(over ? "**yes**" : "no")} |");
        }
        // motion: entrances caught mid-flight (each entering element's Play clip sampled at time t, the rest held)
        var motionDir = Path.GetFullPath("review/motion"); Directory.CreateDirectory(motionDir);
        foreach (var f in Directory.GetFiles(motionDir, "*.png")) File.Delete(f);
        var moments = new (string cue, float[] ts)[] { ("1", new[] { 3f, 9f }), ("2", new[] { 5f, 12f }), ("2T", new[] { 10f, 30f }), ("3", new[] { 3f }),
            ("4", new[] { 0.8f }), ("4B", new[] { 3f, 6f, 9f, 12f, 15f }), ("4C", new[] { 3f, 6f }), ("5", new[] { 2.5f }), ("6", new[] { 3f, 6f }),
            ("6B", new[] { 3f, 9f }), ("7", new[] { 8f }), ("8", new[] { 1.4f, 2.4f }), ("9", new[] { 1.5f, 4f, 7f }), ("9B", new[] { 1.5f }), ("10", new[] { 2f }) };
        foreach (var (cueId, ts) in moments)
        {
            int ci = cues.FindIndex(c => J.S(c["id"]) == cueId) + 1; if (ci <= 0) continue;
            var entering = J.L(cues[ci - 1]["on"]).Select(e => (string)e).ToList();
            foreach (var t in ts)
            {
                SetAll(false);
                var live = new HashSet<string>();
                for (int k = 0; k < ci; k++) { foreach (var e in J.L(cues[k]["off"])) live.Remove((string)e); foreach (var e in J.L(cues[k]["on"])) live.Add((string)e); }
                foreach (var e in live)
                {
                    if (entering.Contains(e) && twins.TryGetValue($"Talk_{e}_Play", out var p))
                    {
                        p.SetActive(true);
                        foreach (var an in p.GetComponentsInChildren<Animator>(true))
                        {
                            var clip = an.runtimeAnimatorController?.animationClips.FirstOrDefault(); if (clip == null) continue;
                            clip.SampleAnimation(an.gameObject, clip.isLooping ? t % Mathf.Max(0.01f, clip.length) : Mathf.Min(t, clip.length));
                        }
                    }
                    else if (twins.TryGetValue($"Talk_{e}_Hold", out var h)) h.SetActive(true);
                }
                Shot(cam, rt, Path.Combine(motionDir, $"{ci:00}_{cueId}_t{t:00.0}.png"), new Vector3(0, -1.15f, -40.1f), new Vector3(0, 1.0f, 0), 95f);
                Shot(cam, rt, Path.Combine(motionDir, $"{ci:00}_{cueId}_t{t:00.0}_wide.png"), new Vector3(0, 9f, -49.0f), new Vector3(0, 0f, 0f), 85f);
            }
        }
        UnityEngine.Object.DestroyImmediate(cam.gameObject);
        File.WriteAllText("review/PERFORMANCE.md", perf.ToString());
        Debug.Log("[Talk] review shots: " + outDir);
        File.AppendAllText("Logs/SphererebroAutomation.txt", $"{DateTime.Now:yyyy-MM-dd HH:mm:ss} talk review shots written ({cues.Count} cues)\n");
        EditorSceneManager.OpenScene(ScenePath);   // discard: nothing here is saved
    }

    static string WorldBaseline()
    {
        int tris = 0, calls = 0;
        foreach (var n in new[] { "=== VISTA ===", "=== STAGE ===", "=== SPHERE ===" })
        {
            var g = GameObject.Find(n); if (!g) continue;
            foreach (var r in g.GetComponentsInChildren<MeshRenderer>(false))
            {
                var mf = r.GetComponent<MeshFilter>(); if (!mf || !mf.sharedMesh || !r.enabled) continue;
                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tris += (int)mf.sharedMesh.GetIndexCount(s) / 3;
                calls += mf.sharedMesh.subMeshCount;
            }
        }
        return $"{tris:N0} triangles and {calls} draw calls (seating, stage, sphere, all switched-on renderers; before frustum culling)";
    }

    static void Shot(Camera cam, RenderTexture rt, string path, Vector3 eye, Vector3 target, float fov)
    {
        cam.transform.position = eye; cam.transform.LookAt(target); cam.fieldOfView = fov;
        cam.clearFlags = CameraClearFlags.Skybox;
        cam.Render();
        RenderTexture.active = rt;
        var t = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
        t.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); t.Apply();
        RenderTexture.active = null;
        File.WriteAllBytes(path, t.EncodeToPNG());
        UnityEngine.Object.DestroyImmediate(t);
    }
}
