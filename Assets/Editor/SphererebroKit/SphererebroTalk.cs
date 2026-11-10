using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Video;
using J = SphererebroTalkJson;

// THE TALK (Ben, 10 Nov 2026): builds the show under SHOW/Talk from Config/talk_timeline.json (made by tools/talk/choreo.py
// from Config/talk_show.json). Called by SphererebroBuilder.Build. XR Time Machine's Show tab steps through the cues.
//
// Every element becomes up to three "twins", each a registered object (BS Object Id) under the Talk root:
//   Talk_<id>_Play  entrance: an Animator plays the element's AnimationClip from the start whenever the twin is switched on
//   Talk_<id>_Hold  the final pose, no entrance motion (used going back, jumping, or arriving late)
//   Talk_<id>_Exit  from the final pose, the exit clip (only when the element has an exit)
// Looping motion (LED twinkle, star drift, the feed wall's scroll) is a child Animator in every twin.
// Everything starts ACTIVE (a BS Object Id registers in Awake) under a Talk root parked 10 km below the world; the script
// switches every twin off, then brings the root home. Talk lights light only the Talk layer (UserLayer8 = 12), and ambient
// beds are 3D sources with a wide minimum distance, so nothing of the show can be seen or heard before the script runs.
public static class SphererebroTalk
{
    const string Root = "Assets/_Sphererebro/Talk";
    const string Cfg = "Assets/_Sphererebro/Config";
    const string ScriptPath = "Assets/WebRoot/script.js";
    public const int TalkLayer = 12;
    public const float Park = -10000f;

    // The talk was choreographed around the vista seats of the 50 m sphere (talk_show.json "audience"; presenter at
    // (0, -2.65, -36.85)). When the sphere's size moves the seats, the whole show moves with them: the Talk root comes
    // home to the presenter's shift instead of to 0,0,0 (Ben, 2026-11-08: sphere doubled to 100 m). Zero at 50 m.
    public static Vector3 HomeOffset()
    {
        var der = J.O(J.Parse(File.ReadAllText(Cfg + "/Sphererebro.derived.json")));
        var show = J.O(J.Parse(File.ReadAllText(Cfg + "/talk_show.json")));
        var dm = J.Fa(J.G(J.O(J.G(der, "vista")), "daisMount"));
        var pr = J.Fa(J.G(J.O(J.G(show, "audience")), "presenter"));
        if (dm == null || pr == null) return Vector3.zero;
        return new Vector3(dm[0] - pr[0], dm[1] - pr[1], dm[2] - pr[2]);
    }
    static Action<string> Log = s => Debug.Log("[Talk] " + s);
    static Dictionary<string, object> TL;
    static Dictionary<string, Material> Mats = new Dictionary<string, Material>();
    static Dictionary<string, object> MatSpec;
    static readonly CultureInfo C = CultureInfo.InvariantCulture;
    static int warnings;
    public static Transform TalkRoot;
    public static readonly Dictionary<string, Transform[]> Twins = new Dictionary<string, Transform[]>();

    // ================================================================================================= entry
    public static void Build(Transform showGroup, Action<string> log)
    {
        Log = log ?? Log; warnings = 0; Twins.Clear(); savedMeshes.Clear(); openDoors = null; textAsset = null;
        // every generated mesh is rebuilt: start from an empty folder (no stale copies piling up)
        if (AssetDatabase.IsValidFolder($"{Root}/Meshes")) AssetDatabase.DeleteAsset($"{Root}/Meshes");
        var tlPath = Cfg + "/talk_timeline.json";
        if (!File.Exists(tlPath)) { Log("TALK: no Config/talk_timeline.json (run tools/talk/choreo.py): talk not built"); return; }
        foreach (var d in new[] { "Materials", "Textures", "Anim", "Meshes", "Audio", "Models", "Shaders" }) Directory.CreateDirectory($"{Root}/{d}");
        TL = J.O(J.Parse(File.ReadAllText(tlPath)));
        MatSpec = J.O(J.Parse(File.ReadAllText("tools/blender/talk_materials.json")));
        ImportTextures();
        ConfigureModels();
        MakeMaterials();
        var root = new GameObject("Talk"); root.transform.SetParent(showGroup, false);
        root.transform.localPosition = new Vector3(0, Park, 0);
        ObjectId(root); TalkRoot = root.transform;
        var els = J.O(TL["elements"]);
        int n = 0;
        foreach (var kv in els) { BuildElement(root.transform, kv.Key, J.O(kv.Value)); n++; }
        BuildVideoSurfaces(root.transform);
        foreach (var t in root.GetComponentsInChildren<Transform>(true)) if (t.GetComponent<Renderer>() != null) t.gameObject.layer = TalkLayer;
        foreach (var r in root.GetComponentsInChildren<Renderer>(true))
        {
            r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            r.lightProbeUsage = LightProbeUsage.Off; r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        }
        Log($"TALK: {n} elements, {Twins.Count} with twins, {root.GetComponentsInChildren<BS.BSObjectId>(true).Length} object ids, warnings {warnings}");
    }

    static void Warn(string s) { warnings++; Log("TALK WARNING: " + s); }

    static Component ObjectId(GameObject go)
    {
        var oid = go.GetComponent<BS.BSObjectId>();
        if (oid == null) oid = go.AddComponent<BS.BSObjectId>();
        oid.GetType().GetMethod("ForceGenerateId")?.Invoke(oid, null);
        return oid;
    }

    // ================================================================================================= textures + materials
    static string TexOut(string name) => $"{Root}/Textures/{name}";

    static void ImportTextures()
    {
        // generated images (talk/gen) are copied in as they are; CC0 sets: colour, normal (GL), packed metal/smoothness
        if (Directory.Exists("talk/gen"))
            foreach (var f in Directory.GetFiles("talk/gen", "*.png"))
            {
                var dst = TexOut("gen_" + Path.GetFileName(f));
                if (!File.Exists(dst) || File.GetLastWriteTimeUtc(f) > File.GetLastWriteTimeUtc(dst)) File.Copy(f, dst, true);
            }
        var sets = new HashSet<string>();
        foreach (var kv in MatSpec) { var s = J.O(kv.Value); var t = J.S(J.G(s, "tex")); if (t != null) sets.Add(t); }
        foreach (var id in sets)
        {
            var src = $"tools/textures/{id}/{id}_1K-JPG_";
            if (!File.Exists(src + "Color.jpg")) { Warn("texture set missing: " + id); continue; }
            Copy(src + "Color.jpg", TexOut(id + "_Color.jpg"));
            if (File.Exists(src + "NormalGL.jpg")) Copy(src + "NormalGL.jpg", TexOut(id + "_Normal.jpg"));
            var ms = TexOut(id + "_MS.png");
            if (!File.Exists(ms) && File.Exists(src + "Roughness.jpg"))
            {
                var rough = Load(src + "Roughness.jpg"); var metal = File.Exists(src + "Metalness.jpg") ? Load(src + "Metalness.jpg") : null;
                var o = new Texture2D(rough.width, rough.height, TextureFormat.RGBA32, false);
                var rp = rough.GetPixels(); var mp = metal?.GetPixels(); var op = new Color[rp.Length];
                for (int i = 0; i < rp.Length; i++) op[i] = new Color(mp != null ? mp[i].r : 0, 0, 0, 1 - rp[i].r);
                o.SetPixels(op); o.Apply(); File.WriteAllBytes(ms, o.EncodeToPNG());
            }
            if (File.Exists(src + "Opacity.jpg"))
            {
                var ca = TexOut(id + "_ColorA.png");
                if (!File.Exists(ca))
                {
                    var col = Load(src + "Color.jpg"); var op = Load(src + "Opacity.jpg");
                    var cp = col.GetPixels(); var pp = op.GetPixels();
                    for (int i = 0; i < cp.Length; i++) cp[i].a = pp[i].r;
                    var o = new Texture2D(col.width, col.height, TextureFormat.RGBA32, true); o.SetPixels(cp); o.Apply();
                    File.WriteAllBytes(ca, o.EncodeToPNG());
                }
            }
        }
        AssetDatabase.Refresh();
        foreach (var path in Directory.GetFiles($"{Root}/Textures").Where(p => !p.EndsWith(".meta")).Select(p => p.Replace('\\', '/')))
        {
            var ti = AssetImporter.GetAtPath(path) as TextureImporter; if (ti == null) continue;
            bool normal = path.EndsWith("_Normal.jpg"), data = path.EndsWith("_MS.png");
            bool changed = false;
            void Set<T>(Func<T> get, Action<T> set, T v) { if (!EqualityComparer<T>.Default.Equals(get(), v)) { set(v); changed = true; } }
            Set(() => ti.textureType, v => ti.textureType = v, normal ? TextureImporterType.NormalMap : TextureImporterType.Default);
            Set(() => ti.sRGBTexture, v => ti.sRGBTexture = v, !(normal || data));
            Set(() => ti.maxTextureSize, v => ti.maxTextureSize = v, 2048);
            Set(() => ti.mipmapEnabled, v => ti.mipmapEnabled = v, true);
            Set(() => ti.anisoLevel, v => ti.anisoLevel = v, 4);
            var android = ti.GetPlatformTextureSettings("Android");
            if (!android.overridden || android.format != TextureImporterFormat.ASTC_6x6 || android.maxTextureSize != 2048)
            { android.overridden = true; android.maxTextureSize = 2048; android.format = TextureImporterFormat.ASTC_6x6; ti.SetPlatformTextureSettings(android); changed = true; }
            if (changed) ti.SaveAndReimport();
        }
    }

    static void Copy(string a, string b) { if (!File.Exists(b) || File.GetLastWriteTimeUtc(a) > File.GetLastWriteTimeUtc(b)) File.Copy(a, b, true); }
    static Texture2D Load(string p) { var t = new Texture2D(2, 2); t.LoadImage(File.ReadAllBytes(p)); return t; }
    static Texture2D T(string file) => AssetDatabase.LoadAssetAtPath<Texture2D>(TexOut(file));

    static void MakeMaterials()
    {
        var lit = Shader.Find("Universal Render Pipeline/Lit");
        var unlit = Shader.Find("Universal Render Pipeline/Unlit");
        var part = Shader.Find("Universal Render Pipeline/Particles/Unlit");
        foreach (var kv in MatSpec)
        {
            if (kv.Key.StartsWith("_")) continue;
            var s = J.O(kv.Value);
            bool isUnlit = J.G(s, "unlit") is bool u && u, isPart = J.G(s, "particles") is bool pp && pp;
            var shader = isPart ? part : isUnlit ? unlit : lit;
            var path = $"{Root}/Materials/{kv.Key}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(shader); AssetDatabase.CreateAsset(m, path); }
            m.shader = shader;
            var tint = J.Fa(J.G(s, "tint")) ?? new[] { 1f, 1f, 1f };
            var emit = J.Fa(J.G(s, "emit"));
            var tex = J.S(J.G(s, "tex")); var etex = J.S(J.G(s, "emitTex"));
            var alpha = J.S(J.G(s, "alpha"), "opaque");
            float opacity = J.F(J.G(s, "opacity"), 1f);
            Texture2D baseTex = null;
            if (tex != null) baseTex = alpha == "clip" && T(tex + "_ColorA.png") != null ? T(tex + "_ColorA.png") : T(tex + "_Color.jpg");
            if (etex != null) { baseTex = T("gen_" + etex); if (baseTex == null) Warn($"{kv.Key}: generated image {etex} missing"); }
            var col = new Color(tint[0], tint[1], tint[2], opacity);
            if ((isUnlit || isPart) && emit != null) col = new Color(emit[0], emit[1], emit[2], opacity);   // unlit: the glow is the colour
            m.SetColor("_BaseColor", col);
            if (m.HasProperty("_Color")) m.SetColor("_Color", col);
            m.SetTexture("_BaseMap", baseTex);
            float tile = J.F(J.G(s, "tile"), 0f);
            m.SetTextureScale("_BaseMap", Vector2.one);
            if (!isUnlit && !isPart)
            {
                var metalSpec = J.G(s, "metal"); var roughSpec = J.G(s, "rough");
                // inside the sphere there are no reflection probes (CLAUDE.md rule 7): fully metallic surfaces go black
                m.SetFloat("_Metallic", Mathf.Min(0.55f, metalSpec == null ? 0.5f : J.F(metalSpec)));
                m.SetFloat("_Smoothness", roughSpec == null ? 0.5f : 1f - J.F(roughSpec));
                var msTex = tex != null && (metalSpec == null || roughSpec == null) ? T(tex + "_MS.png") : null;
                m.SetTexture("_MetallicGlossMap", msTex);
                if (msTex != null) { m.EnableKeyword("_METALLICSPECGLOSSMAP"); m.SetFloat("_Smoothness", 1f); } else m.DisableKeyword("_METALLICSPECGLOSSMAP");
                var n = tex != null ? T(tex + "_Normal.jpg") : null;
                m.SetTexture("_BumpMap", n); m.SetFloat("_BumpScale", 1f);
                if (n != null) m.EnableKeyword("_NORMALMAP"); else m.DisableKeyword("_NORMALMAP");
                if (emit != null)
                {
                    m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", new Color(emit[0], emit[1], emit[2]));
                    m.SetTexture("_EmissionMap", etex != null ? baseTex : null);
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
                }
                else { m.DisableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.black); }
                bool clip = alpha == "clip";
                m.SetFloat("_AlphaClip", clip ? 1 : 0); m.SetFloat("_Cutoff", 0.5f);
                if (clip) m.EnableKeyword("_ALPHATEST_ON"); else m.DisableKeyword("_ALPHATEST_ON");
                m.SetFloat("_Cull", clip ? 0 : 2);
            }
            Blend(m, alpha);
            if (kv.Key == "TK_RackDoor" || kv.Key == "TK_Glass" || kv.Key == "TK_TankGlass" || kv.Key == "TK_Water" || kv.Key == "TK_Beam" || kv.Key == "TK_BeamHalo")
                m.SetFloat("_Cull", 0);
            m.enableInstancing = true;
            EditorUtility.SetDirty(m);
            Mats[kv.Key] = m;
        }
        AssetDatabase.SaveAssets();
    }

    static void Blend(Material m, string alpha)
    {
        bool tr = alpha == "blend" || alpha == "additive" || alpha == "multiply";
        m.SetFloat("_Surface", tr ? 1 : 0);
        m.SetFloat("_Blend", alpha == "additive" ? 2 : alpha == "multiply" ? 3 : 0);
        m.SetOverrideTag("RenderType", tr ? "Transparent" : alpha == "clip" ? "TransparentCutout" : "Opaque");
        var src = BlendMode.One; var dst = BlendMode.Zero;
        if (alpha == "blend") { src = BlendMode.SrcAlpha; dst = BlendMode.OneMinusSrcAlpha; }
        if (alpha == "additive") { src = BlendMode.SrcAlpha; dst = BlendMode.One; }
        if (alpha == "multiply") { src = BlendMode.DstColor; dst = BlendMode.Zero; }
        m.SetFloat("_SrcBlend", (float)src); m.SetFloat("_DstBlend", (float)dst);
        m.SetFloat("_SrcBlendAlpha", tr ? (float)BlendMode.One : 1f); m.SetFloat("_DstBlendAlpha", tr ? (float)BlendMode.OneMinusSrcAlpha : 0f);
        m.SetFloat("_ZWrite", tr ? 0 : 1);
        if (tr) m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); else m.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
        if (alpha == "additive") m.EnableKeyword("_BLENDMODE_ADD"); else m.DisableKeyword("_BLENDMODE_ADD");
        if (alpha == "multiply") m.EnableKeyword("_BLENDMODE_MULTIPLY"); else m.DisableKeyword("_BLENDMODE_MULTIPLY");
        m.renderQueue = tr ? (int)RenderQueue.Transparent : alpha == "clip" ? (int)RenderQueue.AlphaTest : -1;
        m.SetShaderPassEnabled("DepthOnly", !tr);
        m.SetShaderPassEnabled("ShadowCaster", !tr);
    }

    static Material Mat(string name)
    {
        if (name != null && Mats.TryGetValue(name, out var m)) return m;
        if (name != null) Warn("material missing: " + name);
        return Mats.TryGetValue("TK_RackFrame", out var f) ? f : null;
    }

    // a per-node copy of a material (for an animated alpha the renderer animates its own instance through the Animator)
    static void Remap(GameObject go)
    {
        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
        {
            var ms = r.sharedMaterials;
            for (int i = 0; i < ms.Length; i++)
                if (ms[i] != null && Mats.TryGetValue(ms[i].name.Replace(" (Instance)", ""), out var tm)) ms[i] = tm;
                else if (ms[i] != null) { var nm = ms[i].name.Split('.')[0]; if (Mats.TryGetValue(nm, out var t2)) ms[i] = t2; }
            r.sharedMaterials = ms;
        }
    }

    // ================================================================================================= models
    static void ConfigureModels()
    {
        foreach (var path in Directory.GetFiles($"{Root}/Models", "*.fbx").Select(p => p.Replace('\\', '/')))
        {
            var mi = (ModelImporter)AssetImporter.GetAtPath(path);
            if (mi == null) continue;
            bool changed = mi.materialImportMode != ModelImporterMaterialImportMode.None || mi.importAnimation || !mi.isReadable;
            if (!changed) continue;
            mi.materialImportMode = ModelImporterMaterialImportMode.None;   // TK_ materials come from talk_materials.json by name
            mi.animationType = ModelImporterAnimationType.None;
            mi.importAnimation = false; mi.importCameras = false; mi.importLights = false; mi.importBlendShapes = false;
            mi.isReadable = true;           // merged rack waves read the meshes
            mi.meshCompression = ModelImporterMeshCompression.Off;
            mi.SaveAndReimport();
        }
    }

    static readonly Dictionary<string, string[]> MatNames = new Dictionary<string, string[]>();
    // FBX imported without materials: the submesh order follows the Blender material slots; read the names from the GLB-side
    // sidecar written by tools/blender (talk/models/<asset>.mats.json: {object: [material names]})
    static string[] SlotNames(string asset, string obj)
    {
        var key = asset + "/" + obj;
        if (MatNames.TryGetValue(key, out var v)) return v;
        var p = $"talk/models/{asset}.mats.json";
        if (File.Exists(p))
        {
            var d = J.O(J.Parse(File.ReadAllText(p)));
            foreach (var kv in d) MatNames[asset + "/" + kv.Key] = J.L(kv.Value).Select(x => (string)x).ToArray();
        }
        return MatNames.TryGetValue(key, out v) ? v : null;
    }

    static GameObject Instantiate(string asset, Transform parent)
    {
        var a = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/{asset}.fbx");
        if (a == null) { Warn("model missing: " + asset); var c = GameObject.CreatePrimitive(PrimitiveType.Cube); UnityEngine.Object.DestroyImmediate(c.GetComponent<Collider>()); c.transform.SetParent(parent, false); return c; }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(a, parent);
        PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        foreach (var mr in go.GetComponentsInChildren<MeshRenderer>(true))
        {
            var names = SlotNames(asset, mr.name);
            var mf = mr.GetComponent<MeshFilter>();
            int n = mf && mf.sharedMesh ? mf.sharedMesh.subMeshCount : 1;
            var ms = new Material[n];
            for (int i = 0; i < n; i++) ms[i] = Mat(names != null && i < names.Length ? names[i] : "TK_RackFrame");
            mr.sharedMaterials = ms;
        }
        return go;
    }

    // ================================================================================================= elements
    static void BuildElement(Transform root, string id, Dictionary<string, object> el)
    {
        var nodes = J.L(el["nodes"]).Select(J.O).ToList();
        var play = J.O(el["play"]); var exit = J.O(J.G(el, "exit")); var hold = J.O(el["hold"]);
        var loops = J.L(J.G(el, "loops")) ?? new List<object>();
        var twins = new Transform[3];
        playTracks = J.O(play["tracks"]);
        twins[0] = BuildTwin(root, id, "Play", nodes, null, J.O(play["tracks"]), J.F(play["dur"]), loops);
        twins[1] = BuildTwin(root, id, "Hold", nodes, hold, null, 0, loops);
        if (exit != null) twins[2] = BuildTwin(root, id, "Exit", nodes, hold, J.O(exit["tracks"]), J.F(exit["dur"]), loops);
        Twins[id] = twins;
    }

    static Dictionary<string, object> playTracks;
    static bool tracksHaveScale(string path) => playTracks != null && J.O(J.G(playTracks, path)) is Dictionary<string, object> tr && tr.ContainsKey("s");

    static Transform BuildTwin(Transform root, string id, string kind, List<Dictionary<string, object>> nodes,
        Dictionary<string, object> pose, Dictionary<string, object> tracks, float dur, List<object> loops)
    {
        var twin = new GameObject($"Talk_{id}_{kind}").transform;
        twin.SetParent(root, false);
        ObjectId(twin.gameObject);
        var made = new Dictionary<string, Transform>();
        foreach (var n in nodes.OrderBy(n => ((string)n["path"]).Count(c => c == '/')))
        {
            var path = (string)n["path"];
            var make = J.O(n["make"]) ?? new Dictionary<string, object>();
            var rest = J.O(n["rest"]);
            var parentPath = path.Contains('/') ? path.Substring(0, path.LastIndexOf('/')) : null;
            var parent = parentPath != null ? (made.TryGetValue(parentPath, out var pp) ? pp : Ensure(twin, made, parentPath)) : twin;
            var name = path.Substring(path.LastIndexOf('/') + 1);
            var t = Make(parent, name, make, id);
            made[path] = t;
            ApplyPose(t, rest, make);
            var anchorName = J.S(J.G(make, "anchor"));
            if (anchorName != null)
            {
                var a = t.parent.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == anchorName);
                if (a != null) t.localPosition = t.parent.InverseTransformPoint(a.position) + new Vector3(0, 0, -0.06f);
                else Warn($"{id}: anchor {anchorName} missing");
            }
        }
        // the final pose (Hold, and the start of Exit), keeping each model's own scale (make.scale)
        var makes = nodes.ToDictionary(n => (string)n["path"], n => J.O(n["make"]));
        if (pose != null)
            foreach (var kv in pose)
                if (made.TryGetValue(kv.Key, out var t))
                {
                    var mk = makes.TryGetValue(kv.Key, out var m0) ? m0 : null;
                    // an animated scale ("s" in the tracks) is absolute; a rest scale multiplies the model's scale
                    var p = J.O(kv.Value);
                    bool absolute = tracksHaveScale(kv.Key);
                    ApplyPose(t, p, mk, !absolute);
                }
        // loops: a child Animator on the loop node (every twin)
        foreach (var lo in loops.Select(J.O))
        {
            var lp = (string)lo["path"];
            var lt = made.TryGetValue(lp, out var x) ? x : Ensure(twin, made, lp);
            var clip = new AnimationClip { name = $"{id}_{lp.Replace('/', '_')}_loop" };
            foreach (var kv in J.O(lo["tracks"]))
            {
                var sub = kv.Key;
                var target = sub == "" ? lt : lt.Find(sub);
                if (target == null) { target = new GameObject(sub).transform; target.SetParent(lt, false); }
                AddCurves(clip, sub, target, J.O(kv.Value), lt);
            }
            SetLoop(clip, true);
            AttachAnimator(lt.gameObject, clip, $"{id}_{kind}_{lp.Replace('/', '_')}_loop");
        }
        if (kind == "Hold") Consolidate(twin, id);
        if (tracks != null && tracks.Count > 0)
        {
            var clip = new AnimationClip { name = $"{id}_{kind}" };
            foreach (var kv in tracks)
            {
                var path = kv.Key;
                var t = made.TryGetValue(path, out var x) ? x : Ensure(twin, made, path);
                AddCurves(clip, Rel(twin, t), t, J.O(kv.Value), twin);
            }
            SetLoop(clip, false);
            AttachAnimator(twin.gameObject, clip, $"{id}_{kind}");
        }
        return twin;
    }

    // ---- the held pose costs few draw calls: every still renderer merged by material; looping parts (LED twinkle) merged
    // per loop name with the loop's own Animator. XR Time Machine swaps an element's Play twin for its Hold twin once the
    // entrance has finished (same pose), so long cues (the data hall) run on these.
    static void Consolidate(Transform twin, string id)
    {
        var loopNodes = twin.GetComponentsInChildren<Animator>(true).Select(a => a.transform).ToList();
        bool UnderLoop(Transform t) { for (var p = t; p != null && p != twin; p = p.parent) if (loopNodes.Contains(p)) return true; return false; }
        var still = twin.GetComponentsInChildren<MeshRenderer>(true)
            .Where(r => r.gameObject.activeInHierarchy && r.enabled && !UnderLoop(r.transform) && r.GetComponent<MeshFilter>()?.sharedMesh != null).ToList();
        int before = still.Sum(r => r.sharedMaterials.Length);
        if (before < 6) return;
        var groups = new Dictionary<Material, List<CombineInstance>>();
        var toLocal = twin.worldToLocalMatrix;
        foreach (var r in still)
        {
            var mf = r.GetComponent<MeshFilter>();
            for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
            {
                var m = r.sharedMaterials[Math.Min(s, r.sharedMaterials.Length - 1)];
                if (m == null) continue;
                if (!groups.TryGetValue(m, out var l)) groups[m] = l = new List<CombineInstance>();
                l.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = s, transform = toLocal * r.transform.localToWorldMatrix });
            }
            UnityEngine.Object.DestroyImmediate(r);
            UnityEngine.Object.DestroyImmediate(mf);
        }
        var holder = new GameObject("Merged").transform; holder.SetParent(twin, false);
        foreach (var kv in groups)
        {
            var mesh = new Mesh { indexFormat = IndexFormat.UInt32 };
            mesh.CombineMeshes(kv.Value.ToArray(), true, true);
            mesh = Save(mesh, $"{id}_hold_{kv.Key.name}");
            var go = new GameObject(kv.Key.name); go.transform.SetParent(holder, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh; go.AddComponent<MeshRenderer>().sharedMaterial = kv.Key;
        }
        // loops with the same name (every wave's LEDs_A ...): one merged copy each
        foreach (var byName in loopNodes.GroupBy(t => t.name).Where(g => g.Count() > 1))
        {
            var first = byName.First();
            var mats = new Dictionary<Material, List<CombineInstance>>();
            foreach (var ln in byName)
                foreach (var r in ln.GetComponentsInChildren<MeshRenderer>(true))
                {
                    var mf = r.GetComponent<MeshFilter>(); if (mf == null || mf.sharedMesh == null) continue;
                    var lnToLocal = ln.worldToLocalMatrix;
                    for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
                    {
                        var m = r.sharedMaterials[Math.Min(s, r.sharedMaterials.Length - 1)];
                        if (!mats.TryGetValue(m, out var l)) mats[m] = l = new List<CombineInstance>();
                        l.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = s, transform = toLocal * r.transform.localToWorldMatrix });
                    }
                }
            var node = new GameObject(first.name).transform; node.SetParent(holder, false);
            var meshHolder = new GameObject("Mesh").transform; meshHolder.SetParent(node, false);
            var subs = new List<CombineInstance>(); var ms = new List<Material>();
            foreach (var kv in mats)
            {
                var m = new Mesh { indexFormat = IndexFormat.UInt32 }; m.CombineMeshes(kv.Value.ToArray(), true, true);
                subs.Add(new CombineInstance { mesh = m }); ms.Add(kv.Key);
            }
            var all = new Mesh { indexFormat = IndexFormat.UInt32 }; all.CombineMeshes(subs.ToArray(), false, false);
            all = Save(all, $"{id}_hold_{first.name}");
            meshHolder.gameObject.AddComponent<MeshFilter>().sharedMesh = all;
            meshHolder.gameObject.AddComponent<MeshRenderer>().sharedMaterials = ms.ToArray();
            var an = node.gameObject.AddComponent<Animator>();
            an.runtimeAnimatorController = first.GetComponent<Animator>().runtimeAnimatorController;
            an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            foreach (var ln in byName) UnityEngine.Object.DestroyImmediate(ln.gameObject);
        }
        int after = holder.GetComponentsInChildren<MeshRenderer>(true).Sum(r => r.sharedMaterials.Length);
        Log($"TALK {id}: held pose merged, {before} -> {after} draw calls (+ loops)");
    }

    static Transform Ensure(Transform twin, Dictionary<string, Transform> made, string path)
    {
        if (made.TryGetValue(path, out var t)) return t;
        var parentPath = path.Contains('/') ? path.Substring(0, path.LastIndexOf('/')) : null;
        var parent = parentPath == null ? twin : Ensure(twin, made, parentPath);
        var name = path.Substring(path.LastIndexOf('/') + 1);
        var found = parent.Find(name);
        if (found == null) { found = new GameObject(name).transform; found.SetParent(parent, false); }
        made[path] = found; return found;
    }

    static string Rel(Transform root, Transform t)
    {
        var parts = new List<string>();
        while (t != null && t != root) { parts.Insert(0, t.name); t = t.parent; }
        return string.Join("/", parts);
    }

    static Vector3 V(object o, Vector3 def)
    {
        if (o is double d) return Vector3.one * (float)d;     // a single number: uniform (make.scale 0.7)
        var a = J.Fa(o); return a == null ? def : a.Length == 1 ? Vector3.one * a[0] : new Vector3(a[0], a[1], a[2]);
    }

    static void ApplyPose(Transform t, Dictionary<string, object> p, Dictionary<string, object> make, bool scaleFromMake = true)
    {
        if (p == null) return;
        // an anchored node (a rack's label) keeps the place its anchor gave it
        if (p.ContainsKey("p") && J.G(make, "anchor") == null) t.localPosition = V(p["p"], t.localPosition);
        if (p.ContainsKey("e")) t.localEulerAngles = V(p["e"], t.localEulerAngles);
        if (p.ContainsKey("s"))
        {
            var s = V(p["s"], Vector3.one);
            if (scaleFromMake && make != null && J.G(make, "scale") != null) s = Vector3.Scale(s, V(make["scale"], Vector3.one));
            t.localScale = s;
        }
        else if (scaleFromMake && make != null && J.G(make, "scale") != null) t.localScale = V(make["scale"], Vector3.one);
        if (p.ContainsKey("on")) t.gameObject.SetActive(J.F(p["on"]) > 0.5f);
        if (p.ContainsKey("i")) foreach (var l in t.GetComponents<Light>()) l.intensity = J.F(p["i"]);
        if (p.ContainsKey("v")) foreach (var a in t.GetComponents<AudioSource>()) a.volume = J.F(p["v"]);
        if (p.ContainsKey("doors")) SetDoors(t, J.F(p["doors"]));
    }

    // ---- curves ----------------------------------------------------------------------------------------------------------------
    static void SetLoop(AnimationClip clip, bool loop)
    {
        var st = AnimationUtility.GetAnimationClipSettings(clip); st.loopTime = loop; AnimationUtility.SetAnimationClipSettings(clip, st);
    }

    static void AttachAnimator(GameObject go, AnimationClip clip, string name)
    {
        var cp = $"{Root}/Anim/{name}.anim"; var cc = $"{Root}/Anim/{name}.controller";
        AssetDatabase.DeleteAsset(cp); AssetDatabase.DeleteAsset(cc);
        AssetDatabase.CreateAsset(clip, cp);
        var ctl = AnimatorController.CreateAnimatorControllerAtPathWithClip(cc, clip);
        var an = go.GetComponent<Animator>(); if (an == null) an = go.AddComponent<Animator>();
        an.runtimeAnimatorController = ctl;
        an.cullingMode = AnimatorCullingMode.AlwaysAnimate;
        an.applyRootMotion = false;
    }

    static AnimationCurve Curve(List<object> keys, int comp, bool step)
    {
        var c = new AnimationCurve();
        foreach (var k in keys.Select(J.L))
        {
            float t = J.F(k[0]); float v = J.F(k[1 + Math.Min(comp, k.Count - 2)]);
            c.AddKey(new Keyframe(t, v));
        }
        for (int i = 0; i < c.length; i++)
        {
            var mode = step ? AnimationUtility.TangentMode.Constant : AnimationUtility.TangentMode.Linear;
            AnimationUtility.SetKeyLeftTangentMode(c, i, mode); AnimationUtility.SetKeyRightTangentMode(c, i, mode);
        }
        return c;
    }

    static void AddCurves(AnimationClip clip, string path, Transform t, Dictionary<string, object> tr, Transform clipRoot)
    {
        foreach (var kv in tr)
        {
            var keys = J.L(kv.Value);
            if (keys == null || keys.Count == 0) continue;
            switch (kv.Key)
            {
                case "p":
                    for (int i = 0; i < 3; i++) clip.SetCurve(path, typeof(Transform), "localPosition." + "xyz"[i], Curve(keys, i, false)); break;
                case "e":
                    for (int i = 0; i < 3; i++) clip.SetCurve(path, typeof(Transform), "localEulerAnglesRaw." + "xyz"[i], Curve(keys, i, false)); break;
                case "s":
                    var ms = Vector3.one;
                    for (int i = 0; i < 3; i++) clip.SetCurve(path, typeof(Transform), "localScale." + "xyz"[i], Curve(keys, i, false)); break;
                case "on":
                    clip.SetCurve(path, typeof(GameObject), "m_IsActive", Curve(keys, 0, true)); break;
                case "i":
                    if (t.GetComponent<Light>() != null) clip.SetCurve(path, typeof(Light), "m_Intensity", Curve(keys, 0, false));
                    break;
                case "v":
                    if (t.GetComponent<AudioSource>() != null) clip.SetCurve(path, typeof(AudioSource), "m_Volume", Curve(keys, 0, false));
                    break;
                case "a":
                    foreach (var r in t.GetComponentsInChildren<MeshRenderer>(true))
                    {
                        var rp = Rel(clipRoot, r.transform);
                        var m = r.sharedMaterial; if (m == null) continue;
                        var col = m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor") : Color.white;
                        for (int i = 0; i < 3; i++)
                        {
                            var flat = new AnimationCurve(new Keyframe(0, col[i]), new Keyframe(J.F(J.L(keys.Last())[0]), col[i]));
                            clip.SetCurve(rp, typeof(MeshRenderer), "material._BaseColor." + "rgb"[i], flat);
                        }
                        var ac = Curve(keys, 0, false);
                        var scaled = new AnimationCurve(ac.keys.Select(k => new Keyframe(k.time, k.value * col.a, k.inTangent * col.a, k.outTangent * col.a)).ToArray());
                        clip.SetCurve(rp, typeof(MeshRenderer), "material._BaseColor.a", scaled);
                    }
                    break;
                case "doors":
                    DoorCurves(clip, path, t, keys); break;
            }
        }
    }

    // ---- rack doors (racks_open): from closed to the open variant's door angles ------------------------------------------------
    static Dictionary<string, Quaternion> openDoors;
    static Dictionary<string, Quaternion> OpenDoors()
    {
        if (openDoors != null) return openDoors;
        openDoors = new Dictionary<string, Quaternion>();
        var a = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/server_rack_open.fbx");
        if (a != null) foreach (var n in new[] { "Door_XP", "Door_XN" }) { var d = a.transform.Find(n); if (d) openDoors[n] = d.localRotation; }
        return openDoors;
    }
    static void DoorCurves(AnimationClip clip, string path, Transform rack, List<object> keys)
    {
        foreach (var name in new[] { "Door_XP", "Door_XN" })
        {
            var d = rack.Find(name); if (d == null || !OpenDoors().TryGetValue(name, out var open)) { Warn("doors: " + name + " missing"); continue; }
            var closed = d.localRotation;
            var ex = new AnimationCurve[3]; for (int i = 0; i < 3; i++) ex[i] = new AnimationCurve();
            foreach (var k in keys.Select(J.L))
            {
                var e = Quaternion.Slerp(closed, open, J.F(k[1])).eulerAngles;
                for (int i = 0; i < 3; i++) ex[i].AddKey(new Keyframe(J.F(k[0]), e[i]));
            }
            for (int i = 0; i < 3; i++) clip.SetCurve(path + "/" + name, typeof(Transform), "localEulerAnglesRaw." + "xyz"[i], ex[i]);
        }
    }
    static void SetDoors(Transform rack, float u)
    {
        foreach (var name in new[] { "Door_XP", "Door_XN" })
        {
            var d = rack.Find(name); if (d == null || !OpenDoors().TryGetValue(name, out var open)) continue;
            d.localRotation = Quaternion.Slerp(d.localRotation, open, u);
        }
    }

    // ================================================================================================= node makers
    static Transform Make(Transform parent, string name, Dictionary<string, object> make, string elId)
    {
        Transform t;
        var asset = J.S(J.G(make, "asset")); var part = J.S(J.G(make, "part"));
        if (asset != null)
        {
            var go = Instantiate(asset, parent);
            if (part != null)
            {
                var keep = go.transform.Find(part) ?? go.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == part);
                if (keep == null) { Warn($"{elId}: part {part} not in {asset}"); }
                else
                {
                    var holder = new GameObject(name).transform; holder.SetParent(parent, false);
                    keep.SetParent(holder, false); keep.localPosition = Vector3.zero; keep.localRotation = Quaternion.identity;
                    UnityEngine.Object.DestroyImmediate(go);
                    go = holder.gameObject;
                }
            }
            go.name = name; t = go.transform;
            var mo = J.S(J.G(make, "mat")); if (mo != null) foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.sharedMaterials = r.sharedMaterials.Select(_ => Mat(mo)).ToArray();
            var ma = J.S(J.G(make, "matAlpha")); if (ma != null) foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.sharedMaterials = r.sharedMaterials.Select(_ => Mat(ma)).ToArray();
            return t;
        }
        if (part != null)   // an existing part of the parent's asset (e.g. the tank's Water)
        {
            var found = parent.Find(name) ?? parent.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == part);
            if (found != null) { found.name = name; return found; }
            Warn($"{elId}: part {part} not found under {parent.name}");
        }
        t = new GameObject(name).transform; t.SetParent(parent, false);
        if (J.G(make, "merge") != null) MakeMerge(t, make, elId);
        else if (J.G(make, "special") != null) MakeSpecial(t, make, elId);
        else if (J.G(make, "light") != null) MakeLight(t, J.O(make["light"]));
        else if (J.G(make, "audio") != null) MakeAudio(t, J.O(make["audio"]));
        else if (J.G(make, "text") != null) MakeText(t, make, elId);
        else if (J.G(make, "glyph") != null) MakeGlyph(t, make);
        else if (J.G(make, "timeline") != null) SphererebroTalkTimeline.Make(t, make, TL, Mat);
        return t;
    }

    static void MakeLight(Transform t, Dictionary<string, object> L)
    {
        var l = t.gameObject.AddComponent<Light>();
        var type = J.S(L["type"]);
        l.type = type == "spot" ? LightType.Spot : type == "directional" ? LightType.Directional : LightType.Point;
        var c = J.Fa(L["color"]); l.color = new Color(c[0], c[1], c[2]);
        l.intensity = J.F(L["intensity"]);
        l.range = J.F(J.G(L, "range"), 30);
        if (l.type == LightType.Spot) { l.spotAngle = J.F(J.G(L, "angle"), 60); l.innerSpotAngle = l.spotAngle * 0.55f; }
        l.shadows = LightShadows.None;
        l.lightmapBakeType = LightmapBakeType.Realtime;
        l.renderMode = LightRenderMode.Auto;
        l.cullingMask = 1 << TalkLayer;             // talk lights light only the talk (and never the world, even at load)
    }

    static void MakeAudio(Transform t, Dictionary<string, object> A)
    {
        var clipName = J.S(A["clip"]);
        var clip = AssetDatabase.LoadAssetAtPath<AudioClip>($"{Root}/Audio/{clipName}");
        if (clip == null) Warn("audio missing: " + clipName);
        var a = t.gameObject.AddComponent<AudioSource>();
        a.clip = clip; a.playOnAwake = true; a.loop = J.G(A, "loop") is bool b && b; a.volume = J.F(A["vol"], 1);
        float spatial = J.F(J.G(A, "spatial"), 1f);
        // 3D always: a "2D" bed is a 3D source with a huge minimum distance and full spread (so a twin parked 10 km away at
        // load is silent, and at home it sounds the same everywhere in the sphere)
        a.spatialBlend = 1f;
        a.rolloffMode = AudioRolloffMode.Linear;
        if (spatial < 0.5f) { a.minDistance = 300; a.maxDistance = 900; a.spread = 360; }
        else { a.minDistance = J.F(J.G(A, "min"), 10); a.maxDistance = J.F(J.G(A, "max"), 500); a.spread = (1 - spatial) * 360; }
        a.dopplerLevel = 0.6f;
        a.priority = a.loop ? 64 : 100;
    }

    // ---- text: word meshes from talk_text.fbx (tools/blender/talk_text.py) ----------------------------------------------------
    static GameObject textAsset;
    static Transform TextMesh(string name)
    {
        if (textAsset == null) textAsset = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/talk_text.fbx");
        return textAsset == null ? null : textAsset.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == name);
    }

    static Transform Word(Transform parent, string src, string name, float size, Material mat)
    {
        var srcT = TextMesh(src);
        // a wrapper (unscaled: the fade animates its scale around 1) holding the mesh at the text size
        var go = new GameObject(name);
        go.transform.SetParent(parent, false);
        if (srcT == null) { Warn("text mesh missing: " + src); return go.transform; }
        go.transform.localPosition = srcT.localPosition * size;
        var m = new GameObject("M"); m.transform.SetParent(go.transform, false);
        m.AddComponent<MeshFilter>().sharedMesh = srcT.GetComponent<MeshFilter>().sharedMesh;
        m.AddComponent<MeshRenderer>().sharedMaterial = mat;
        m.transform.localScale = Vector3.one * size;
        return go.transform;
    }

    static void MakeText(Transform t, Dictionary<string, object> make, string elId)
    {
        var key = J.S(make["text"]); int line = (int)J.F(J.G(make, "line"), 0);
        if (J.G(make, "sub") != null) key += "sub";
        float size = J.F(make["size"], 1); var mat = Mat(J.S(make["mat"]));
        float arc = J.F(J.G(make, "arc"), 0);
        int wi = 0;
        var words = new List<Transform>();
        while (true)
        {
            var src = $"{key}_L{line}_W{wi:00}";
            if (TextMesh(src) == null) break;
            words.Add(Word(t, src, $"W{wi:00}", size, mat)); wi++;
        }
        if (wi == 0) { Warn($"{elId}: no text meshes for {key} line {line}"); return; }
        if (arc > 0)
            foreach (var w in words)
            {
                float x = w.localPosition.x, th = x / arc;
                w.localPosition = new Vector3(arc * Mathf.Sin(th), w.localPosition.y, -arc + arc * Mathf.Cos(th));
                w.localRotation = Quaternion.Euler(0, th * Mathf.Rad2Deg, 0);
            }
        var anchor = J.S(J.G(make, "anchor"));
        if (anchor != null)
        {
            var a = t.parent.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == anchor);
            if (a != null) { t.localPosition = t.parent.InverseTransformPoint(a.position) + new Vector3(0, 0, -0.05f); }
            else Warn($"{elId}: anchor {anchor} missing");
        }
        if (J.G(make, "frame") is bool fr && fr)
        {
            // a stamp's ink border around the words
            var b = words.Select(w => w.GetComponentInChildren<MeshRenderer>()).Where(r => r).Select(r => r.bounds).Aggregate((x, y) => { x.Encapsulate(y); return x; });
            var lb = new Bounds(t.InverseTransformPoint(b.center), b.size);
            float pad = size * 0.35f, th = size * 0.12f;
            var ink = new GameObject("Frame"); ink.transform.SetParent(t, false);
            var mesh = new Mesh();
            var v = new List<Vector3>(); var tri = new List<int>();
            void Q(Vector3 a, Vector3 c)
            {
                int i = v.Count; v.Add(new Vector3(a.x, a.y, 0)); v.Add(new Vector3(c.x, a.y, 0)); v.Add(new Vector3(c.x, c.y, 0)); v.Add(new Vector3(a.x, c.y, 0));
                tri.AddRange(new[] { i, i + 2, i + 1, i, i + 3, i + 2 });
            }
            float x0 = lb.min.x - pad, x1 = lb.max.x + pad, y0 = lb.min.y - pad, y1 = lb.max.y + pad;
            Q(new Vector3(x0, y0), new Vector3(x1, y0 + th)); Q(new Vector3(x0, y1 - th), new Vector3(x1, y1));
            Q(new Vector3(x0, y0), new Vector3(x0 + th, y1)); Q(new Vector3(x1 - th, y0), new Vector3(x1, y1));
            mesh.SetVertices(v); mesh.SetTriangles(tri, 0); mesh.RecalculateNormals(); mesh.RecalculateBounds();
            mesh = Save(mesh, $"{elId}_inkframe");
            ink.AddComponent<MeshFilter>().sharedMesh = mesh; ink.AddComponent<MeshRenderer>().sharedMaterial = mat;
        }
    }

    static void MakeGlyph(Transform t, Dictionary<string, object> make)
    {
        var g = J.S(make["glyph"]);
        var key = g == "$" ? "glyph_dollar" : g == "." ? "glyph_point" : "glyph_" + g;
        var w = Word(t, key, "Glyph", J.F(make["size"], 1), Mat(J.S(make["mat"])));
        w.localPosition = Vector3.zero;   // the node is the glyph's place; its scale stays 1 (alpha and on/off animate the node)
    }

    // ---- merged rack waves: one renderer per wave for the bodies, LEDs in two blinking halves, contact shadows ---------------
    static void MakeMerge(Transform t, Dictionary<string, object> make, string elId)
    {
        var items = J.L(make["merge"]).Select(J.O).ToList();
        var split = J.O(J.G(make, "split"));
        var splitNames = new HashSet<string>();
        if (split != null) foreach (var kv in split) foreach (var n in J.L(kv.Value)) splitNames.Add((string)n);
        var body = new Dictionary<Material, List<CombineInstance>>();
        var leds = new[] { new Dictionary<Material, List<CombineInstance>>(), new Dictionary<Material, List<CombineInstance>>() };
        var shadow = new List<CombineInstance>();
        var tmp = new GameObject("tmp"); tmp.transform.SetParent(t, false);
        for (int i = 0; i < items.Count; i++)
        {
            var it = items[i];
            var go = Instantiate(J.S(it["asset"]), tmp.transform);
            go.transform.localPosition = V(it["p"], Vector3.zero);
            go.transform.localRotation = Quaternion.Euler(0, J.F(it["yaw"]), 0);
            go.transform.localScale = J.G(it, "s") != null ? Vector3.one * J.F(it["s"]) : Vector3.one;
            var toLocal = t.worldToLocalMatrix;
            foreach (var mr in go.GetComponentsInChildren<MeshRenderer>(true))
            {
                var mf = mr.GetComponent<MeshFilter>(); if (mf == null || mf.sharedMesh == null) continue;
                var dict = splitNames.Contains(mr.name) ? leds[i % 2] : body;
                for (int s = 0; s < mf.sharedMesh.subMeshCount; s++)
                {
                    var m = mr.sharedMaterials[Math.Min(s, mr.sharedMaterials.Length - 1)];
                    if (!dict.TryGetValue(m, out var l)) dict[m] = l = new List<CombineInstance>();
                    l.Add(new CombineInstance { mesh = mf.sharedMesh, subMeshIndex = s, transform = toLocal * mr.transform.localToWorldMatrix });
                }
            }
            if (J.G(make, "shadows") is bool sh && sh)
                shadow.Add(new CombineInstance { mesh = ShadowQuad(), transform = toLocal * go.transform.localToWorldMatrix });
        }
        UnityEngine.Object.DestroyImmediate(tmp);
        MergedObject(t, "Body", body, elId);
        for (int h = 0; h < 2; h++)
        {
            var holder = new GameObject(h == 0 ? "LEDs_A" : "LEDs_B").transform; holder.SetParent(t, false);
            MergedObject(holder, "Mesh", leds[h], elId);
        }
        if (shadow.Count > 0)
        {
            var sm = new Mesh { indexFormat = IndexFormat.UInt32 }; sm.CombineMeshes(shadow.ToArray(), true, true);
            sm = Save(sm, $"{elId}_{t.name}_shadow");
            var so = new GameObject("Shadow"); so.transform.SetParent(t, false);
            so.AddComponent<MeshFilter>().sharedMesh = sm; so.AddComponent<MeshRenderer>().sharedMaterial = Mat("TK_Shadow");
        }
    }

    static Mesh shadowQuad;
    static Mesh ShadowQuad()
    {
        if (shadowQuad != null) return shadowQuad;
        // a soft contact shadow under a 12 x 18 m footprint (unity: x 12, z 18), 2 cm above the floor
        shadowQuad = new Mesh();
        float hx = 9f, hz = 12f;
        shadowQuad.vertices = new[] { new Vector3(-hx, 0.02f, -hz), new Vector3(hx, 0.02f, -hz), new Vector3(hx, 0.02f, hz), new Vector3(-hx, 0.02f, hz) };
        shadowQuad.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(1, 1), new Vector2(0, 1) };
        shadowQuad.triangles = new[] { 0, 2, 1, 0, 3, 2 };
        shadowQuad.RecalculateNormals();
        return shadowQuad;
    }

    static void MergedObject(Transform parent, string name, Dictionary<Material, List<CombineInstance>> parts, string elId)
    {
        if (parts.Count == 0) return;
        var subs = new List<CombineInstance>(); var mats = new List<Material>();
        int k = 0;
        foreach (var kv in parts)
        {
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.CombineMeshes(kv.Value.ToArray(), true, true);
            subs.Add(new CombineInstance { mesh = m, transform = Matrix4x4.identity }); mats.Add(kv.Key); k++;
        }
        var mesh = new Mesh { indexFormat = IndexFormat.UInt32 };
        mesh.CombineMeshes(subs.ToArray(), false, false);
        mesh.RecalculateBounds();
        mesh = Save(mesh, $"{elId}_{parent.parent?.name}_{parent.name}_{name}");
        var go = new GameObject(name); go.transform.SetParent(parent, false);
        go.AddComponent<MeshFilter>().sharedMesh = mesh;
        go.AddComponent<MeshRenderer>().sharedMaterials = mats.ToArray();
    }

    static readonly HashSet<string> savedMeshes = new HashSet<string>();
    // one asset per name per build: the twins (Play, Hold, Exit) build the same meshes, and share them
    public static Mesh Save(Mesh m, string name)
    {
        name = string.Concat(name.Select(ch => char.IsLetterOrDigit(ch) || ch == '_' ? ch : '_'));
        var p = $"{Root}/Meshes/{name}.asset";
        if (savedMeshes.Contains(p)) { var had = AssetDatabase.LoadAssetAtPath<Mesh>(p); if (had != null) return had; }
        savedMeshes.Add(p);
        m.name = name;
        AssetDatabase.CreateAsset(m, p);
        return m;
    }

    // ---- specials ---------------------------------------------------------------------------------------------------------
    static void MakeSpecial(Transform t, Dictionary<string, object> make, string elId)
    {
        var kind = J.S(make["special"]);
        switch (kind)
        {
            case "envsphere": EnvSphere(t, J.F(make["radius"]), (int)J.F(J.G(make, "segments"), 48), Mat(J.S(make["mat"])), elId); break;
            case "stars": Stars(t, J.F(make["radius"]), (int)J.F(make["count"]), (int)J.F(J.G(make, "seed"), 1), Mat(J.S(make["mat"])), elId); break;
            case "floor": Floor(t, J.F(make["size"]), J.F(make["y"]), Mat(J.S(make["mat"])), elId); break;
            case "feedsector": SphererebroTalkFeed.Sector(t, make, Mat, elId); break;
            case "shatter": Shatter(t, make); break;
            case "dust": Dust(t, make); break;
            default: Warn("unknown special " + kind); break;
        }
    }

    static void EnvSphere(Transform t, float r, int seg, Material mat, string elId)
    {
        var mesh = SphereMesh(r, seg, seg / 2, true, 0f, 1f, -90f, 90f);
        mesh = Save(mesh, $"{elId}_envsphere");
        t.gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
        t.gameObject.AddComponent<MeshRenderer>().sharedMaterial = mat;
    }

    // a UV sphere (inside-out when inward); u runs with the compass angle (u 0.5 = straight ahead, +Z), v bottom -> top
    public static Mesh SphereMesh(float r, int seg, int rings, bool inward, float u0, float u1, float lat0, float lat1, float lon0 = -180f, float lon1 = 180f)
    {
        var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
        for (int j = 0; j <= rings; j++)
        {
            float lat = Mathf.Deg2Rad * Mathf.Lerp(lat0, lat1, j / (float)rings);
            for (int i = 0; i <= seg; i++)
            {
                float lon = Mathf.Deg2Rad * Mathf.Lerp(lon0, lon1, i / (float)seg);
                v.Add(new Vector3(r * Mathf.Cos(lat) * Mathf.Sin(lon), r * Mathf.Sin(lat), r * Mathf.Cos(lat) * Mathf.Cos(lon)));
                uv.Add(new Vector2(Mathf.Lerp(u0, u1, i / (float)seg), j / (float)rings));
            }
        }
        for (int j = 0; j < rings; j++)
            for (int i = 0; i < seg; i++)
            {
                int a = j * (seg + 1) + i, b = a + seg + 1;
                if (inward) tri.AddRange(new[] { a, b, a + 1, a + 1, b, b + 1 });
                else tri.AddRange(new[] { a, a + 1, b, a + 1, b + 1, b });
            }
        var m = new Mesh { indexFormat = IndexFormat.UInt32 };
        m.SetVertices(v); m.SetUVs(0, uv); m.SetTriangles(tri, 0);
        m.RecalculateNormals(); m.RecalculateBounds();
        return m;
    }

    static void Stars(Transform t, float r, int count, int seed, Material mat, string elId)
    {
        var rnd = new System.Random(seed);
        var v = new List<Vector3>(); var uv = new List<Vector2>(); var col = new List<Color>(); var tri = new List<int>();
        var eye = new Vector3(0, -1, -43);
        for (int i = 0; i < count; i++)
        {
            // uniform on the shell, more toward the horizon band
            double z = rnd.NextDouble() * 2 - 1, phi = rnd.NextDouble() * Math.PI * 2;
            var dir = new Vector3((float)(Math.Sqrt(1 - z * z) * Math.Cos(phi)), (float)z, (float)(Math.Sqrt(1 - z * z) * Math.Sin(phi)));
            var p = dir * r;
            float mag = (float)Math.Pow(rnd.NextDouble(), 3.0);
            float size = 0.05f + 0.32f * mag;
            float temp = (float)rnd.NextDouble();
            var c = Color.Lerp(new Color(0.75f, 0.85f, 1f), new Color(1f, 0.88f, 0.7f), temp) * (0.35f + 0.9f * mag);
            c.a = 1;
            var f = (eye - p).normalized; var right = Vector3.Cross(Vector3.up, f).normalized; if (right.sqrMagnitude < 0.1f) right = Vector3.right;
            var up = Vector3.Cross(f, right);
            int b = v.Count;
            v.Add(p + (-right - up) * size); v.Add(p + (right - up) * size); v.Add(p + (right + up) * size); v.Add(p + (-right + up) * size);
            uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(1, 0)); uv.Add(new Vector2(1, 1)); uv.Add(new Vector2(0, 1));
            for (int k = 0; k < 4; k++) col.Add(c);
            tri.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3 });
        }
        var m = new Mesh { indexFormat = IndexFormat.UInt32 };
        m.SetVertices(v); m.SetUVs(0, uv); m.SetColors(col); m.SetTriangles(tri, 0); m.RecalculateBounds();
        m.bounds = new Bounds(Vector3.zero, Vector3.one * r * 2.2f);
        m = Save(m, $"{elId}_stars");
        t.gameObject.AddComponent<MeshFilter>().sharedMesh = m;
        var mr = t.gameObject.AddComponent<MeshRenderer>();
        var star = Mat("TK_Stars"); if (star != null && T("gen_particle_soft.png") != null) star.SetTexture("_BaseMap", T("gen_particle_soft.png"));
        mr.sharedMaterial = mat;
    }

    static void Floor(Transform t, float size, float y, Material mat, string elId)
    {
        var m = new Mesh();
        float h = size / 2, tile = 8f;
        m.vertices = new[] { new Vector3(-h, y, -h), new Vector3(h, y, -h), new Vector3(h, y, h), new Vector3(-h, y, h) };
        m.uv = new[] { new Vector2(0, 0), new Vector2(size / tile, 0), new Vector2(size / tile, size / tile), new Vector2(0, size / tile) };
        m.triangles = new[] { 0, 2, 1, 0, 3, 2 }; m.RecalculateNormals(); m.RecalculateBounds();
        m = Save(m, $"{elId}_floor");
        t.gameObject.AddComponent<MeshFilter>().sharedMesh = m;
        t.gameObject.AddComponent<MeshRenderer>().sharedMaterial = mat;
    }

    // white-room dust: slow grey specks in a big box ahead of the audience (prewarmed: it is simply there)
    static void Dust(Transform t, Dictionary<string, object> make)
    {
        var size = J.Fa(make["size"]); var c = J.Fa(make["center"]);
        var ps = t.gameObject.AddComponent<ParticleSystem>();
        var main = ps.main; main.loop = true; main.prewarm = true; main.playOnAwake = true; main.duration = 30;
        main.startLifetime = 30; main.startSpeed = new ParticleSystem.MinMaxCurve(0.05f, 0.4f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.35f);
        main.maxParticles = (int)J.F(make["count"], 1500); main.simulationSpace = ParticleSystemSimulationSpace.Local;
        main.startColor = new Color(1, 1, 1, 1);
        var em = ps.emission; em.rateOverTime = main.maxParticles / 30f;
        var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Box; sh.scale = new Vector3(size[0], size[1], size[2]); sh.position = new Vector3(c[0], c[1], c[2]);
        var noise = ps.noise; noise.enabled = true; noise.strength = 0.3f; noise.frequency = 0.05f;
        var col = ps.colorOverLifetime; col.enabled = true;
        var g = new Gradient(); g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
            new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, 0.15f), new GradientAlphaKey(1, 0.85f), new GradientAlphaKey(0, 1) });
        col.color = g;
        var r = t.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = Mat("TK_Dust"); r.renderMode = ParticleSystemRenderMode.Billboard;
        r.maxParticleSize = 0.05f;
    }

    static void Shatter(Transform t, Dictionary<string, object> make)
    {
        var ps = t.gameObject.AddComponent<ParticleSystem>();
        var main = ps.main;
        main.duration = 6f; main.loop = false; main.playOnAwake = true;
        main.startLifetime = new ParticleSystem.MinMaxCurve(3.0f, 5.5f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(2.5f, 11f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.45f);
        main.startColor = new ParticleSystem.MinMaxGradient(new Color(1, 1, 1, 1), new Color(0.85f, 0.92f, 1f, 1));
        main.gravityModifier = -0.04f;
        main.maxParticles = (int)J.F(make["count"], 4000);
        main.simulationSpace = ParticleSystemSimulationSpace.Local;
        main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
        var em = ps.emission; em.rateOverTime = 0;
        em.SetBursts(new[] { new ParticleSystem.Burst(0f, (short)main.maxParticles) });
        var sh = ps.shape;
        sh.shapeType = ParticleSystemShapeType.Circle;
        sh.radius = J.F(make["radius"], 16); sh.radiusThickness = 0.02f;
        sh.arc = 2 * J.F(make["arc"], 95);
        sh.rotation = new Vector3(90, 0, 90 + J.F(make["arc"], 95));    // the arc around the audience, in front
        sh.scale = new Vector3(1, 1, 1);
        // spread the ring up the wall's height
        sh.position = new Vector3(0, (J.F(make["y0"]) + J.F(make["y1"])) / 2, 0);
        var noise = ps.noise; noise.enabled = true; noise.strength = 0.8f; noise.frequency = 0.25f;
        var col = ps.colorOverLifetime; col.enabled = true;
        var g = new Gradient();
        g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(new Color(0.9f, 0.95f, 1f), 1) },
                  new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, 0.05f), new GradientAlphaKey(0.9f, 0.5f), new GradientAlphaKey(0, 1) });
        col.color = g;
        var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.EaseInOut(0, 1, 1, 0.3f));
        var vel = ps.velocityOverLifetime; vel.enabled = true; vel.space = ParticleSystemSimulationSpace.Local;
        vel.y = new ParticleSystem.MinMaxCurve(-1.5f, 4f); vel.x = new ParticleSystem.MinMaxCurve(0, 0); vel.z = new ParticleSystem.MinMaxCurve(0, 0);
        var r = t.GetComponent<ParticleSystemRenderer>();
        r.sharedMaterial = Mat("TK_Particle");
        r.renderMode = ParticleSystemRenderMode.Billboard;
        r.maxParticleSize = 0.08f;
        // the burst is a ring: also a second, taller emitter (box) would cost more; the vertical spread comes from velocity
    }

    // ================================================================================================= video surfaces
    // Video objects are NOT twins (one player per surface and layout): the script sets the url on the one a cue asks for.
    // mono: URP Unlit (the SDK's standard path); sbs / tb: SB/StereoVideo (unity_StereoEyeIndex picks the half per eye).
    static void BuildVideoSurfaces(Transform root)
    {
        var stereo = Shader.Find("SB/StereoVideo");
        if (stereo == null) Warn("shader SB/StereoVideo missing: stereo layouts fall back to the left eye (mono shader with tiling)");
        var screenEl = J.O(J.G(J.O(TL["elements"]), "screen"));
        var vid = J.O(J.G(screenEl, "video"));
        var pos = vid != null ? V(vid["pos"], new Vector3(0, -9, -13)) : new Vector3(0, -9, -13);
        Mesh curved = null;
        var cs = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/curved_screen.fbx");
        var scr = cs ? cs.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault(m => m.name == "Screen") : null;
        if (scr) curved = scr.sharedMesh; else Warn("curved_screen Screen mesh missing");
        var dome360 = SphereMesh(47.5f, 96, 48, true, 0f, 1f, -90f, 90f);
        dome360 = Save(dome360, "video_dome360");
        var dome180 = SphereMesh(47.5f, 64, 48, true, 0f, 1f, -90f, 90f, -90f, 90f);
        dome180 = Save(dome180, "video_dome180");
        var surfaces = new (string name, Mesh mesh, Vector3 pos, Matrix4x4 local)[]
        {
            ("curved", curved, pos + new Vector3(0, 0, -0.03f), Matrix4x4.identity),
            ("dome360", dome360, Vector3.zero, Matrix4x4.identity),
            ("dome180", dome180, Vector3.zero, Matrix4x4.identity),
        };
        foreach (var s in surfaces)
            foreach (var layout in new[] { "mono", "sbs", "tb" })
            {
                var go = new GameObject($"Talk_Video_{s.name}_{layout}");
                go.transform.SetParent(root, false);
                go.transform.localPosition = s.pos;
                if (s.mesh == null) continue;
                go.AddComponent<MeshFilter>().sharedMesh = s.mesh;
                var mr = go.AddComponent<MeshRenderer>();
                Material m;
                var mp = $"{Root}/Materials/TK_Video_{s.name}_{layout}.mat";
                m = AssetDatabase.LoadAssetAtPath<Material>(mp);
                var sh = layout == "mono" || stereo == null ? Shader.Find("Universal Render Pipeline/Unlit") : stereo;
                if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, mp); }
                m.shader = sh;
                m.SetColor("_BaseColor", Color.white);
                if (layout != "mono" && stereo != null) m.SetFloat("_Layout", layout == "sbs" ? 1 : 2);
                if (layout != "mono" && stereo == null) m.SetTextureScale("_BaseMap", layout == "sbs" ? new Vector2(0.5f, 1) : new Vector2(1, 0.5f));
                if (layout == "tb" && stereo == null) m.SetTextureOffset("_BaseMap", new Vector2(0, 0.5f));
                m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>("Assets/_Sphererebro/Textures/Black4.png"));
                mr.sharedMaterial = m;
                var vp = go.AddComponent<VideoPlayer>();
                vp.playOnAwake = false; vp.isLooping = false; vp.waitForFirstFrame = true; vp.skipOnDrop = true;
                vp.renderMode = VideoRenderMode.MaterialOverride; vp.targetMaterialRenderer = mr; vp.targetMaterialProperty = "_BaseMap";
                vp.audioOutputMode = VideoAudioOutputMode.AudioSource;
                var au = go.AddComponent<AudioSource>();
                au.playOnAwake = false; au.spatialBlend = s.name == "curved" ? 1f : 0.3f; au.minDistance = 25; au.maxDistance = 200; au.rolloffMode = AudioRolloffMode.Linear;
                vp.SetTargetAudioSource(0, au);
                var bsv = go.AddComponent<BS.BSVideoPlayer>();
                var f = bsv.GetType().GetField("routeAudioThroughAudioSource", System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic);
                f?.SetValue(bsv, true);
                ObjectId(go);
            }
    }

    // ================================================================================================= script.js block
    const string BlockStart = "// >>> Sphererebro talk show", BlockEnd = "// <<< Sphererebro talk show";
    static void WriteScriptBlock()
    {
        var els = J.O(TL["elements"]);
        var elOut = new Dictionary<string, object>();
        foreach (var kv in els)
        {
            var e = J.O(kv.Value);
            var o = new Dictionary<string, object>
            {
                ["play"] = $"Talk_{kv.Key}_Play", ["hold"] = $"Talk_{kv.Key}_Hold",
                ["exit"] = J.G(e, "exit") != null ? $"Talk_{kv.Key}_Exit" : null,
                ["playDur"] = J.F(J.O(e["play"])["dur"]), ["exitDur"] = J.G(e, "exit") != null ? J.F(J.O(e["exit"])["dur"]) : 0f,
            };
            if (J.G(e, "video") != null) o["video"] = e["video"];
            elOut[kv.Key] = o;
        }
        var cues = J.L(TL["cues"]).Select(J.O).Select(c => (object)new Dictionary<string, object>
        {
            ["id"] = c["id"], ["name"] = c["name"], ["on"] = c["on"], ["off"] = c["off"], ["video"] = J.G(c, "video"),
        }).ToList();
        var show = new Dictionary<string, object>
        {
            ["title"] = "IPN talk, 10 Nov 2026", ["root"] = "Talk", ["home"] = new List<object> { (double)HomeOffset().x, (double)HomeOffset().y, (double)HomeOffset().z },
            ["mediaBase"] = TL["mediaBase"], ["elements"] = elOut, ["cues"] = cues,
            ["videos"] = new List<object> { "curved", "dome360", "dome180" }.SelectMany(s => new[] { "mono", "sbs", "tb" }.Select(l => (object)$"Talk_Video_{s}_{l}")).ToList(),
            ["rehearsalSeconds"] = 20.0,
        };
        var block = BlockStart + " (generated by SphererebroTalk from Config/talk_show.json via talk_timeline.json; do not edit)\n" +
                    "window.SB_TALK = " + J.Write(show) + ";\n" + BlockEnd;
        var js = File.ReadAllText(ScriptPath);
        int s0 = js.IndexOf(BlockStart, StringComparison.Ordinal), e0 = js.IndexOf(BlockEnd, StringComparison.Ordinal);
        string next;
        if (s0 < 0 || e0 < s0)
        {
            // first time: put it just before the XR Time Machine config (which reads it)
            var cfg = js.IndexOf("// >>> XR Time Machine config", StringComparison.Ordinal);
            if (cfg < 0) { Warn("script.js: no XR Time Machine config block; talk block not written"); return; }
            next = js.Substring(0, cfg) + block + "\n\n" + js.Substring(cfg);
        }
        else next = js.Substring(0, s0) + block + js.Substring(e0 + BlockEnd.Length);
        if (next != js) { File.WriteAllText(ScriptPath, next, new UTF8Encoding(false)); Log("script.js: talk show block updated"); }
        else Log("script.js: talk show block unchanged");
    }
}
