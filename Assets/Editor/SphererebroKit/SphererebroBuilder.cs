using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using TMPro;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// Builds the whole Sphererebro scene from the FBX files made by ../Assets/scripts/build_sphererebro.py (Blender).
// Menu: Sphererebro > Build World (and Build World + Bake Lighting). Batch: -executeMethod SphererebroBuilder.BuildBatch
// (add -sbBake to bake). The scene is REBUILT from scratch every run: change this file or the Blender script, not the
// scene, or your hand edits are lost on the next build. Report: Logs/SphererebroBuilder.txt.
//
// Frame: origin = sphere centre = dais pivot; centre floor, bridge deck and concourse floor at y 0; the bridge runs to -Z
// (6 o'clock). phi is the compass angle from +Z (12 o'clock), clockwise seen from above: position (r sin phi, y, r cos phi).
public static class SphererebroBuilder
{
    const string Root = "Assets/_Sphererebro";
    const string ScenePath = Root + "/Scenes/Sphererebro.unity";
    const string DerivedPath = Root + "/Config/Sphererebro.derived.json";
    const string ScriptPath = "Assets/WebRoot/script.js";
    const int UI = 5, Grabbable = 20, Invisible = 21;

    static readonly StringBuilder Report = new StringBuilder();
    static void Log(string s) { Report.AppendLine(s); }

    // ---- size: Config/Sphererebro.derived.json (written by the Blender generator from Sphererebro.dims.json) ------------
    // Every sphere-scale position here comes from it, so resizing the sphere is: edit dims.json, run Blender, build.
    [Serializable] public class DConcourse { public float r0, r1, height, phi0, phi1, barPhi0, barPhi1, barFaceR, barTopY, loungeR, coveInR, coveOutR, reflectionProbeR; public float[] loungePhis, probeRadii, reflectionProbeSize; }
    [Serializable] public class DPlaza { public float y, radius; public float[] center, facadeWash, spawnGlow; }
    [Serializable] public class DNav { public float[] spawn, bandArrival, ringDest, daisDest; }
    [Serializable] public class DBridge { public float[] @out; public float inZ, inY, segLength; }
    [Serializable] public class DRescue { public float y; public float[] size; }
    [Serializable] public class DEsc { public float[] stepPitch, foot, top; }
    // the vista layout (seats: flat [row, x, y, z, ...]; housePos: flat [x, y, z, ...]: JsonUtility reads no nested arrays)
    [Serializable] public class DVista { public float[] daisMount, landing, daisDest, keyPos, keyTarget, housePos, seats; public float stageY; public int seatCount; }
    [Serializable] public class DZones { public float[] edges; public string[] names; }
    [Serializable] public class Derived { public float sphereRadius, domeClipRadius; public DConcourse concourse; public DPlaza plaza; public DNav nav; public DBridge bridge; public DRescue rescue; public DEsc escalator; public string seating; public DVista vista; public DZones zones; }

    // ---- club lighting zones along the concourse (Ben, 2026-11-07: tinted in places, no green); the Blender script names
    // the zones and tints the coves and sconces, this colours their baked lights the same
    static readonly Dictionary<string, Color> ZoneColor = new Dictionary<string, Color>
    {
        ["Rose"] = new Color(1f, 0.38f, 0.6f), ["Amber"] = new Color(1f, 0.66f, 0.38f),
        ["Blue"] = new Color(0.4f, 0.55f, 1f), ["Violet"] = new Color(0.68f, 0.38f, 1f),
    };
    static Color ZoneAt(float phi)
    {
        var z = D.zones;
        if (z == null || z.edges == null) return ZoneColor["Amber"];
        for (int i = 0; i + 1 < z.edges.Length; i++)
            if (phi >= z.edges[i] && phi <= z.edges[i + 1]) return ZoneColor.TryGetValue(z.names[i], out var c) ? c : ZoneColor["Amber"];
        return ZoneColor["Amber"];
    }

    // ---- the IPN cube show (2026-11-07): Ben's IPN logo cube (SB_IPNCube.fbx, made by ..\Assets\scripts\import_ipn_cube.py
    // from his IPN-Cube2.blend, 10 m across), halfway between the audience and the far wall, with three realtime lights of
    // its own: a warm key from above the audience, and two coloured rims from behind for the edges. Everything starts
    // ACTIVE (an Object Id registers in Awake); the script hides the cube and its lights at load and shows them only while
    // the show runs (SB.show in script.js: pose, timing, the IPN CUBE desk key). Not static: it moves.
    static readonly Vector3 CubeCentre = new Vector3(0, 1.0f, 3.2f);   // the same numbers as SB.show.centre in script.js
    static void SetupIpnCube(Transform show)
    {
        var path = $"{Root}/Models/SB_IPNCube.fbx";
        if (AssetDatabase.LoadAssetAtPath<GameObject>(path) == null) { Log("IPN cube: no SB_IPNCube.fbx (run import_ipn_cube.py)"); return; }
        var cube = Place("SB_IPNCube", show);
        cube.name = "IPN_Cube";
        cube.SetPositionAndRotation(CubeCentre, Quaternion.Euler(-90, 0, 0) * Quaternion.Euler(0, 180, 0));   // the IMMERSIVE pose
        foreach (var r in cube.GetComponentsInChildren<MeshRenderer>(true)) { r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false; }
        ObjectId(cube.gameObject);
        int tris = cube.GetComponentsInChildren<MeshFilter>(true).Sum(m => m.sharedMesh != null ? (int)m.sharedMesh.GetIndexCount(0) / 3 : 0);
        Light L(string name, Vector3 pos, Color c, float intensity, float range, float angle)
        {
            var l = AddLight(show, name, LightType.Spot, pos, Quaternion.LookRotation(CubeCentre - pos), c, intensity, range, LightmapBakeType.Realtime, angle);
            l.renderMode = LightRenderMode.ForcePixel;
            l.gameObject.AddComponent<BS.BSLight>(); ObjectId(l.gameObject);
            return l;
        }
        L("Cube Key", new Vector3(0, 10f, -12f), new Color(1f, 0.9f, 0.78f), 40f, 30f, 42f);
        L("Cube Rim A", new Vector3(-10f, 7f, 15f), new Color(0.35f, 0.6f, 1f), 30f, 24f, 45f);
        L("Cube Rim B", new Vector3(10f, 7f, 15f), new Color(1f, 0.35f, 0.75f), 30f, 24f, 45f);
        Log($"IPN cube: at {CubeCentre}, first-level tris {tris}, 3 realtime lights (on only during the show)");
    }

    // ---- things Ben has taken out (2026-11-07), switched off, not deleted: the green planter "obelisks" (concourse and
    // plaza) and the star inlays (spawn pad, dais) until an on-brand motif replaces them. Their lights stay: they light the
    // plaza, not the fittings.
    static readonly string[] Retired = { "Band_Planter_", "Plaza_Planter_", "Plaza_SpawnPad", "Dais_Inlay", "Dais_Perch_", "Sphere_Portal_Flange" };   // + the dais stools, the square flange round the arch (2026-11-07)
    static void RetireRemoved(GameObject[] roots)
    {
        int n = 0;
        foreach (var t in roots.SelectMany(r => All(r.transform)).Where(t => Retired.Any(t.name.StartsWith)).ToList())
        { t.gameObject.SetActive(false); n++; }
        Log($"retired (switched off): {n} objects (planters, star inlays)");
    }
    // which audience layout is live (dims.json "seating"): "vista" (default) or "round". Both are built; the other is switched off.
    static bool Vista => D.seating != "round";
    static Derived D;
    static Vector3 V(float[] a) => new Vector3(a[0], a[1], a[2]);

    static Derived LoadDerived()
    {
        if (!File.Exists(DerivedPath)) throw new Exception(DerivedPath + " missing: run the Blender generator first (CLAUDE.md, pipeline step 1)");
        var d = JsonUtility.FromJson<Derived>(File.ReadAllText(DerivedPath));
        Log($"size: sphere r {d.sphereRadius}, concourse {d.concourse.r0}-{d.concourse.r1}, plaza {d.plaza.center[2]}");
        return d;
    }

    [MenuItem("Sphererebro/Build World")]
    public static void BuildMenu() => Build(false);

    [MenuItem("Sphererebro/Build World + Bake Lighting")]
    public static void BuildAndBakeMenu() => Build(true);

    public static void BuildBatch() => Build(Environment.GetCommandLineArgs().Contains("-sbBake"));

    // Unity recompiles editor scripts only after a menu command returns, so the first Build World after this code changes
    // would run the OLD builder (seen 2026-11-07: a build kept RIDE after it was removed). Refuse, and say why.
    static bool StaleBuilder()
    {
        var dll = "Library/ScriptAssemblies/Assembly-CSharp-Editor.dll";
        if (!File.Exists(dll)) return false;
        var built = File.GetLastWriteTimeUtc(dll);
        return Directory.GetFiles("Assets/Editor/SphererebroKit", "*.cs").Any(f => File.GetLastWriteTimeUtc(f) > built.AddSeconds(2));
    }

    // for SphererebroAutomation (a Claude session building while Ben is away): false if the code is stale
    public static bool BuildForAutomation(bool bake)
    {
        if (StaleBuilder()) return false;
        Build(bake);
        return true;
    }

    static void Build(bool bake)
    {
        if (StaleBuilder())
        {
            const string msg = "The Sphererebro builder's scripts changed and Unity hasn't compiled them yet, so this build would run the old version.\n\nWait for Unity to finish compiling (the spinner, bottom right), then run Build World again.";
            Debug.LogWarning("[Sphererebro] " + msg);
            if (Application.isBatchMode) throw new Exception(msg);
            AssetDatabase.Refresh();
            EditorUtility.DisplayDialog("Sphererebro", msg, "OK");
            return;
        }
        Report.Clear();
        Log("Sphererebro build " + DateTime.Now.ToString("yyyy-MM-dd HH:mm"));
        AssetDatabase.Refresh();
        foreach (var d in new[] { "Materials", "Scenes", "Animation", "Prefabs", "Settings" })
            Directory.CreateDirectory(Path.Combine(Root, d));
        D = LoadDerived();
        var link = ReadWorldLink();
        var mats = SphererebroMaterials.MakeAll();
        ConfigureModels();
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        WriteWorldLink(link);
        var groups = new Dictionary<string, Transform>();
        foreach (var g in new[] { "ENVIRONMENT", "SPHERE", "CONCOURSE", "PLAZA", "BRIDGE", "STAGE", "VISTA", "PROPS", "SHOW", "LIGHTING", "NAVIGATION", "SAFETY", "EVENTS" })
            groups[g] = new GameObject($"=== {g} ===").transform;
        new GameObject("Environment").transform.SetParent(groups["ENVIRONMENT"], false);
        Log("seating: " + (Vista ? "VISTA (round theatre and bridge off)" : "ROUND (vista off)"));

        var sphere = Place("SB_Sphere", groups["SPHERE"]);
        var band = Place("SB_Band", groups["CONCOURSE"]);
        var plaza = Place("SB_Plaza", groups["PLAZA"]);
        var bridge = Place("SB_Bridge", groups["BRIDGE"]);
        var stage = Place("SB_Stage", groups["STAGE"]);
        var vista = Place("SB_Vista", groups["VISTA"]);
        // SHOW: the show system's assets (spec phase 3). First one: the IPN cube (2026-11-07)
        SetupIpnCube(groups["SHOW"]);

        SetupColliders(scene.GetRootGameObjects());
        SetupSphere(sphere, mats);
        SetupBridge(bridge);
        SetupStage(stage);
        PlaceRecliners(groups["STAGE"]);
        PlaceVistaRecliners(groups["VISTA"]);
        SetupDesk(stage);
        SetupRide(stage);
        PlaceProps(band, groups["PROPS"]);
        SeatBarStools(band);
        SetupEscalator(plaza);
        SetupNavigation(groups["NAVIGATION"], groups["SAFETY"], plaza);
        SetupLighting(groups["LIGHTING"], band, plaza);
        MarkStatic(band, true); MarkStatic(plaza, true);
        MarkStatic(sphere, false, "Sphere_Load_Ring_EMIT"); MarkStatic(stage, false, "Dais_Floor_Rotating"); MarkStatic(vista, false);
        foreach (var z in new[] { sphere, stage, bridge, groups["STAGE"], groups["VISTA"], groups["SHOW"] }) RealtimeOnly(z);
        RenderSettingsSetup(mats);
        RetireRemoved(scene.GetRootGameObjects());
        WriteScriptDims();
        ApplySeating(Vista);

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        if (bake)
        {
            Log("baking lighting...");
            var ok = Lightmapping.Bake();
            Log("bake " + (ok ? "done" : "FAILED") + ", lightmaps: " + LightmapSettings.lightmaps.Length);
            EditorSceneManager.SaveScene(scene, ScenePath);
        }
        Stats(scene.GetRootGameObjects());
        Directory.CreateDirectory("Logs");
        File.WriteAllText("Logs/SphererebroBuilder.txt", Report.ToString());
        Debug.Log("[Sphererebro] build done\n" + Report);
    }

    // ---- models -----------------------------------------------------------------------------------------------------------
    static void ConfigureModels()
    {
        foreach (var path in Directory.GetFiles(Root + "/Models", "SB_*.fbx").Select(p => p.Replace('\\', '/')))
            ConfigureModel(path);
    }

    static void ConfigureModel(string path)
    {
        {
            var mi = (ModelImporter)AssetImporter.GetAtPath(path);
            if (mi == null) return;
            var file = Path.GetFileNameWithoutExtension(path);
            mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            mi.materialLocation = ModelImporterMaterialLocation.InPrefab;
            mi.animationType = ModelImporterAnimationType.None;
            mi.importAnimation = false; mi.importCameras = false; mi.importLights = false;
            mi.importBlendShapes = false;
            mi.isReadable = file == "SB_Props" || file == "SB_Bridge" || file == "SB_Stage";
            mi.generateSecondaryUV = file == "SB_Band" || file == "SB_Plaza";
            mi.meshCompression = ModelImporterMeshCompression.Medium;
            mi.SaveAndReimport();
            mi.SearchAndRemapMaterials(ModelImporterMaterialName.BasedOnMaterialName, ModelImporterMaterialSearch.RecursiveUp);
            mi.SaveAndReimport();
        }
    }

    static Transform Place(string model, Transform parent)
    {
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/{model}.fbx");
        if (asset == null) throw new Exception("missing model " + model);
        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent);
        PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
        go.name = model.Substring(3);
        return go.transform;
    }

    // ---- the Builder's link to the world (BS World Link: world id + slug) lives in the scene; a rebuild must keep it -------
    static (string id, string slug) ReadWorldLink()
    {
        var text = File.Exists(ScenePath) ? File.ReadAllText(ScenePath) : "";
        var i = text.IndexOf("BS.BSWorldLink", StringComparison.Ordinal);
        var block = i < 0 ? "" : text.Substring(i, Math.Min(400, text.Length - i));
        var id = System.Text.RegularExpressions.Regex.Match(block, @"worldId:[ \t]*'?(\d+)").Groups[1].Value;
        var slug = System.Text.RegularExpressions.Regex.Match(block, @"slug:[ \t]*'?([A-Za-z0-9_-]*)").Groups[1].Value;   // same line only: may be empty
        if (string.IsNullOrEmpty(id))
        {
            // fallback: the Builder's own memory of the selected world (Assets/ProjectPrefs.asset)
            var prefs = File.Exists("Assets/ProjectPrefs.asset") ? File.ReadAllText("Assets/ProjectPrefs.asset") : "";
            id = System.Text.RegularExpressions.Regex.Match(prefs, @"BanterBuilder_selectedWorldId\s+Type:\s*\d+\s+Value:\s*(\d+)").Groups[1].Value;
            if (!string.IsNullOrEmpty(id)) Log("world link: id taken from ProjectPrefs");
        }
        Log($"world link kept: id {id}, slug {slug}");
        return (id, slug);
    }

    // BSWorldLink.worldId and slug are strings (BSWorldLink.cs); a holder named __WorldLink, tagged EditorOnly, as the Builder makes it
    static void WriteWorldLink((string id, string slug) link)
    {
        if (string.IsNullOrEmpty(link.id)) { Log("world link: NONE, the Builder will ask for a world"); return; }
        var go = new GameObject(BS.BSWorldLink.HolderName) { tag = "EditorOnly" };
        var wl = go.AddComponent<BS.BSWorldLink>();
        wl.worldId = link.id; wl.slug = link.slug;
        EditorUtility.SetDirty(wl);
    }

    // ---- the world script's size block: generated here from derived.json, between markers in script.js ------------------
    const string DimsStart = "// >>> Sphererebro dims", DimsEnd = "// <<< Sphererebro dims";
    static void WriteScriptDims()
    {
        var c = System.Globalization.CultureInfo.InvariantCulture;
        string F(float f) => f.ToString("0.####", c);
        string A(float[] a) => "[" + string.Join(", ", a.Select(F)) + "]";
        var block = DimsStart + " (generated by SphererebroBuilder from Config/Sphererebro.derived.json; do not edit)\n" +
            "const SB_DIMS = {\n" +
            $"    sphereRadius: {F(D.sphereRadius)}, domeClipRadius: {F(D.domeClipRadius)},\n" +
            $"    bridgeOut: {A(D.bridge.@out)}, bridgeInZ: {F(D.bridge.inZ)}, bridgeInY: {F(D.bridge.inY)},\n" +
            $"    spawn: {A(D.nav.spawn)}, bandArrival: {A(D.nav.bandArrival)}, ringDest: {A(D.nav.ringDest)},\n" +
            $"    seating: \"{(Vista ? "vista" : "round")}\",\n" +
            (D.escalator.foot != null ? $"    escalator: {{ foot: {A(D.escalator.foot)}, top: {A(D.escalator.top)} }},\n" : "") +
            "};\n" + DimsEnd;
        var js = File.ReadAllText(ScriptPath);
        int s = js.IndexOf(DimsStart, StringComparison.Ordinal), e = js.IndexOf(DimsEnd, StringComparison.Ordinal);
        if (s < 0 || e < s) throw new Exception("script.js has no '" + DimsStart + "' block");
        var next = js.Substring(0, s) + block + js.Substring(e + DimsEnd.Length);
        if (next != js) { File.WriteAllText(ScriptPath, next, new UTF8Encoding(false)); Log("script.js: dims block updated"); }
        else Log("script.js: dims block unchanged");
    }

    static Transform Find(Transform root, string name) =>
        root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name);

    static IEnumerable<Transform> All(Transform root) => root.GetComponentsInChildren<Transform>(true);

    static Component ObjectId(GameObject go)
    {
        var oid = go.GetComponent<BS.BSObjectId>();
        if (oid == null) oid = go.AddComponent<BS.BSObjectId>();
        oid.GetType().GetMethod("ForceGenerateId")?.Invoke(oid, null);
        return oid;
    }

    // ---- colliders by name --------------------------------------------------------------------------------------------------
    // *_COL: collider only (renderer removed); walls, rails, gates and sides go on Invisible (21): solid, invisible, and they
    // stop teleport arcs. Floors and walkable decks keep a renderer and get an exact MeshCollider.
    static readonly string[] Walkable = { "_Floor", "Plaza_Stairs", "Ring_Steps" };
    static readonly string[] Solid = { "Band_Wall_Outer", "Band_Wall_End", "Band_Wall_Inner", "Band_Bar_BackBar", "Band_Lounge_Sofa",
        "Band_Lounge_Table", "Band_StandingTable", "Band_BarStool", "Band_Planter", "Plaza_Planter", "Band_Restroom_Door", "Desk_Body", "Esc_Body" };

    static void SetupColliders(GameObject[] roots)
    {
        int cols = 0;
        foreach (var t in roots.SelectMany(r => All(r.transform)))
        {
            var mf = t.GetComponent<MeshFilter>();
            if (mf == null) continue;
            var n = t.name;
            if (n.Contains("_COL"))
            {
                var mr = t.GetComponent<MeshRenderer>(); if (mr != null) UnityEngine.Object.DestroyImmediate(mr);
                var mc = t.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh;
                t.gameObject.layer = new[] { "Wall", "Rail", "Gate", "Side" }.Any(n.Contains) ? Invisible : 0;
                cols++;
            }
            else if (Walkable.Any(n.Contains) || Solid.Any(n.StartsWith))
            {
                var mc = t.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; cols++;
            }
        }
        Log($"colliders: {cols}");
    }

    // ---- sphere: lit panels (dark by default), glowing panels, video screen, lattice ---------------------------------------
    static void SetupSphere(Transform sphere, Dictionary<string, Material> mats)
    {
        var inner = Find(sphere, "Sphere_Shell_Inner");
        // Every object the script toggles starts ACTIVE: a BS Object Id registers in Awake, so an object that loads inactive
        // can never be found. Inside out: screen (49.6 m, black until a video plays), glow (49.95 m), lit panels (50 m).
        // With no script at all the screen hides the rest: pitch dark. The script picks the mode at load.
        var glow = UnityEngine.Object.Instantiate(inner.gameObject, inner.parent);
        glow.name = "Sphere_Shell_Glow";
        glow.transform.localScale = Vector3.one * 0.999f;
        glow.GetComponent<MeshRenderer>().sharedMaterial = mats["SB_SolarPanel_Glow"];
        var screen = Find(sphere, "Sphere_Screen");
        foreach (var go in new[] { inner.gameObject, glow, screen.gameObject, Find(sphere, "Sphere_Lattice").gameObject })
            ObjectId(go);
        // the video loading ring (2026-11-07): the script shows and spins it while a dome video loads (never static)
        var ring = Find(sphere, "Sphere_Load_Ring_EMIT"); if (ring != null) ObjectId(ring.gameObject);
        foreach (var r in sphere.GetComponentsInChildren<MeshRenderer>(true))
        {
            r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = false;
            r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        }
        // the video plays on the screen sphere's own mesh; the script sets its url and turns it on
        screen.gameObject.AddComponent<BS.BSVideoPlayer>();
    }

    // ---- bridge: three segments and the drawspan move (script), so kinematic bodies; gates toggle -------------------------
    static void SetupBridge(Transform bridge)
    {
        foreach (var n in new[] { "Bridge_Seg_01", "Bridge_Seg_02", "Bridge_Seg_03", "Bridge_Drawspan" })
        {
            var t = Find(bridge, n);
            ObjectId(t.gameObject);
            var rb = t.gameObject.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
        }
    }

    static void SetupStage(Transform stage)
    {
        foreach (var n in new[] { "Ring_Gate_Inner_COL", "Ring_Gate_Outer_COL", "Dais_Gate_COL" })
            ObjectId(Find(stage, n).gameObject);
        var dais = Find(stage, "Dais_Floor_Rotating");
        ObjectId(dais.gameObject);
        var rb = dais.gameObject.AddComponent<Rigidbody>(); rb.isKinematic = true; rb.useGravity = false;
        var mc = dais.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = dais.GetComponent<MeshFilter>().sharedMesh;
        foreach (var r in stage.GetComponentsInChildren<MeshRenderer>(true)) r.shadowCastingMode = ShadowCastingMode.Off;
    }

    // ---- recliners: 33 on the inner row, 35 on the outer, each over 330 deg (the 30 deg carve-out at 6 o'clock) -------------
    public const float Row1R = 5.4f, Row2R = 7.1f, TierH = 0.5f;
    static void PlaceRecliners(Transform stageGroup)
    {
        var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SB_Recliner.fbx");
        var src = model.GetComponentInChildren<MeshFilter>(true);   // a one-object FBX imports with the mesh on its root
        var srcMr = src.GetComponent<MeshRenderer>();
        foreach (var (row, count, r, y) in new[] { (1, 33, Row1R, 0f), (2, 35, Row2R, TierH) })
        {
            var grp = new GameObject($"Recliners Row {row}").transform; grp.SetParent(stageGroup, false);
            float step = 330f / count;
            for (int i = 0; i < count; i++)
            {
                float phi = 195f + step * (i + 0.5f);
                var pos = Polar(r, phi, y);
                var go = new GameObject($"Recliner R{row} {i + 1:00}");
                go.transform.SetParent(grp, false);
                go.transform.position = pos;
                go.transform.rotation = Quaternion.LookRotation(new Vector3(-pos.x, 0, -pos.z).normalized, Vector3.up);
                MakeRecliner(go, src, srcMr);
            }
        }
        Log("recliners: 33 + 35");
    }

    // One recliner: mesh, colliders, drink holders and the seat. Local frame: front (+Z) toward the stage, origin on the floor.
    // 2026-11-07: footrests gone, sit point 8 cm further forward (Ben: knees went through the cushion); the body collider
    // no longer covers the arms, so a glass dropped in a drink holder rests in it (each holder is a cup of thin boxes).
    static void MakeRecliner(GameObject go, MeshFilter src, MeshRenderer srcMr)
    {
        go.AddComponent<MeshFilter>().sharedMesh = src.sharedMesh;
        var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = srcMr.sharedMaterials;
        mr.shadowCastingMode = ShadowCastingMode.Off;
        void Box(Vector3 c, Vector3 s) { var b = go.AddComponent<BoxCollider>(); b.center = c; b.size = s; }
        Box(new Vector3(0, 0.6f, -0.05f), new Vector3(0.58f, 1.2f, 0.7f));                 // seat and back, between the arms
        foreach (var side in new[] { -1f, 1f })
        {
            Box(new Vector3(side * 0.37f, 0.3f, -0.06f), new Vector3(0.17f, 0.6f, 0.76f)); // arm, up to just under the holder
            // drink holder at Blender (side*0.37, -0.2) = Unity (-side*0.37, z 0.2): floor at 0.66, walls to 0.72, 9.4 cm inside
            var h = new Vector3(-side * 0.37f, 0f, 0.2f);
            Box(h + new Vector3(0, 0.655f, 0), new Vector3(0.11f, 0.01f, 0.11f));
            foreach (var (dx, dz) in new[] { (1f, 0f), (-1f, 0f), (0f, 1f), (0f, -1f) })
                Box(h + new Vector3(dx * 0.052f, 0.69f, dz * 0.052f), new Vector3(dz != 0 ? 0.11f : 0.01f, 0.07f, dx != 0 ? 0.11f : 0.01f));
        }
        AddSeat(go.transform, "Seat", new Vector3(0, 0.46f, 0.06f), Quaternion.identity, new Vector3(0, 0.1f, -0.06f), new Vector3(0.6f, 0.56f, 0.7f));
    }

    // ---- vista seating (Ben, 2026-11-07): the same recliners in a fan of raked rows just inside the portal, every seat facing
    // the sphere centre (so the far hemisphere), positions from derived.json (the Blender generator computes the rows) -------
    static void PlaceVistaRecliners(Transform vistaGroup)
    {
        var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SB_Recliner.fbx");
        var src = model.GetComponentInChildren<MeshFilter>(true);
        var srcMr = src.GetComponent<MeshRenderer>();
        var grp = new GameObject("Recliners Vista").transform; grp.SetParent(vistaGroup, false);
        var s = D.vista.seats; int n = 0;
        var perRow = new Dictionary<int, int>();
        for (int i = 0; i + 3 < s.Length; i += 4)
        {
            int row = Mathf.RoundToInt(s[i]); var pos = new Vector3(s[i + 1], s[i + 2], s[i + 3]);
            perRow[row] = perRow.TryGetValue(row, out var c) ? c + 1 : 1;
            var go = new GameObject($"Recliner V{row} {perRow[row]:00}");
            go.transform.SetParent(grp, false);
            go.transform.position = pos;
            go.transform.rotation = Quaternion.LookRotation(new Vector3(-pos.x, 0, -pos.z).normalized, Vector3.up);
            MakeRecliner(go, src, srcMr);
            n++;
        }
        Log($"vista recliners: {n} in {perRow.Count} rows ({string.Join(", ", perRow.OrderBy(kv => kv.Key).Select(kv => kv.Value))})");
    }

    // The dais (floor, desk, buttons, joystick, perches, RIDE zone: all its children) moves onto the vista stage, under a
    // mount. At HOME (yaw 0) the desk faces the dome, like the audience (Ben, 2026-11-07), and its open side faces the aisle,
    // so the presenter walks straight in. TURN still works (kept for now; in VR the presenter can turn themselves). The
    // script turns the dais in its local frame exactly as before. Its walls and gate stay behind with the round theatre
    // (switched off): Ben, "remove the walls on the side of the dais". BRIDGE and DRAWSPAN have nothing to move here.
    // The mount carries an Object Id: the world script finds it to know it is in the vista layout (it can only be found
    // while the VISTA group is on), so the script always matches the scene, whichever way it was toggled.
    static void MoveDaisToVista(Transform dais, Transform vistaGroup)
    {
        var mount = Find(vistaGroup, "Vista_Dais_Mount");
        if (mount == null) { mount = new GameObject("Vista_Dais_Mount").transform; mount.SetParent(vistaGroup, false); }
        ObjectId(mount.gameObject);
        mount.position = V(D.vista.daisMount); mount.rotation = Quaternion.identity;   // HOME: the desk faces the dome
        dais.SetParent(mount, false);
        dais.localPosition = Vector3.zero; dais.localRotation = Quaternion.identity;
    }

    // ---- switching the audience layout -------------------------------------------------------------------------------------
    // The layout that isn't live is kept, switched off (Ben: keep it, turn it off; never delete). In vista: the round ring
    // and its seats, the bridge, and the concourse portal gate (it only stands while the bridge is away; vista has no
    // bridge, the entry deck is always there). The dais moves between the two, the in-sphere lights and the rescue landing
    // move to suit. Everything here is real-time or a collider, so switching needs no rebake. Used by Build World (with
    // dims.json "seating") and by the Seating menu (the open scene, unsaved).
    static void ApplySeating(bool vista)
    {
        var roots = UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects();
        Transform G(string n) => roots.FirstOrDefault(r => r.name == $"=== {n} ===")?.transform;
        Transform stageGroup = G("STAGE"), vistaGroup = G("VISTA"), bridgeGroup = G("BRIDGE"), band = G("CONCOURSE");
        Transform lighting = G("LIGHTING"), nav = G("NAVIGATION");
        var stageRoot = stageGroup.Cast<Transform>().FirstOrDefault(t => t.name == "Stage");
        var dais = Find(stageGroup, "Dais_Floor_Rotating") ?? (vistaGroup != null ? Find(vistaGroup, "Dais_Floor_Rotating") : null);
        if (vista && vistaGroup == null) throw new Exception("this scene has no vista layout yet");
        if (dais != null)
        {
            if (vista) MoveDaisToVista(dais, vistaGroup);
            else { dais.SetParent(stageRoot, false); dais.localPosition = Vector3.zero; dais.localRotation = Quaternion.identity; }
            foreach (var key in new[] { "Bridge", "Drawspan" })
            {
                var label = Find(dais, "Label_" + key);
                var tmp = label != null ? label.GetComponent<TextMeshPro>() : null;
                if (tmp != null) tmp.text = vista ? "—" : ButtonLabels[key];
            }
        }
        stageRoot.gameObject.SetActive(!vista);
        foreach (var t in stageGroup.Cast<Transform>().Where(t => t.name.StartsWith("Recliners Row"))) t.gameObject.SetActive(!vista);
        if (bridgeGroup != null) bridgeGroup.gameObject.SetActive(!vista);
        var gate = band != null ? Find(band, "Band_Gate_COL") : null; if (gate != null) gate.gameObject.SetActive(!vista);
        if (vistaGroup != null) vistaGroup.gameObject.SetActive(vista);
        if (lighting != null)
        {
            var key = Find(lighting, "Dais Key");
            if (key != null) { var p = KeyPose(vista); key.SetPositionAndRotation(p.pos, p.rot); }
            for (int i = 0; i < 3; i++)
            {
                var h = Find(lighting, $"House {i + 1}");
                if (h != null) { var p = HousePose(vista, i); h.SetPositionAndRotation(p.pos, p.rot); }
            }
        }
        if (nav != null)
        {
            var ring = Find(nav, "Nav_RingDest"); if (ring != null) ring.position = V(vista ? D.vista.landing : D.nav.ringDest);
            var dd = Find(nav, "Nav_DaisDest"); if (dd != null) dd.position = V(vista ? D.vista.daisDest : D.nav.daisDest);
        }
        Log(vista ? $"seating VISTA: dais on the vista stage at {V(D.vista.daisMount)} (desk faces the dome at HOME), round theatre, bridge and portal gate off"
                  : "seating ROUND: dais back at the centre, vista off");
    }

    // in-sphere real-time lights for each layout (same names, so the script's LIGHTS presets reach them either way)
    static (Vector3 pos, Quaternion rot) KeyPose(bool vista)
    {
        if (!vista) return (new Vector3(0, 7f, 0.8f), Quaternion.LookRotation(new Vector3(0, -1f, -0.1f)));
        var p = V(D.vista.keyPos); return (p, Quaternion.LookRotation(V(D.vista.keyTarget) - p));
    }
    static (Vector3 pos, Quaternion rot) HousePose(bool vista, int i)
    {
        if (!vista)
        {
            var p = Polar(6.3f, 60f + 120f * i, 7f);
            return (p, Quaternion.LookRotation(new Vector3(0, -1f, 0) + new Vector3(p.x, 0, p.z).normalized * 0.15f));
        }
        var h = D.vista.housePos; return (new Vector3(h[3 * i], h[3 * i + 1], h[3 * i + 2]), Quaternion.LookRotation(Vector3.down, Vector3.forward));
    }

    // ---- Seating menu: switch the OPEN scene between the layouts, for a look. No build, no bake, nothing saved: keep it
    // with File > Save, or throw it away by reopening the scene without saving. If the scene predates the vista layout,
    // the first switch adds the vista pieces to it (model, seats, colliders), exactly as Build World would.
    [MenuItem("Sphererebro/Seating/Vista (preview in the open scene)")]
    public static void SeatingVistaMenu() => PreviewSeating(true);

    [MenuItem("Sphererebro/Seating/Round (preview in the open scene)")]
    public static void SeatingRoundMenu() => PreviewSeating(false);

    public static void PreviewSeating(bool vista)
    {
        Report.Clear();
        var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene();
        var roots = scene.GetRootGameObjects();
        var stageGroup = roots.FirstOrDefault(r => r.name == "=== STAGE ===");
        if (stageGroup == null) { EditorUtility.DisplayDialog("Sphererebro", "Open the Sphererebro scene first.", "OK"); return; }
        D = LoadDerived();
        if (vista && !roots.Any(r => r.name == "=== VISTA ==="))
        {
            var vistaGroup = new GameObject("=== VISTA ===").transform;
            vistaGroup.SetSiblingIndex(stageGroup.transform.GetSiblingIndex() + 1);
            ConfigureModel($"{Root}/Models/SB_Vista.fbx");
            var vroot = Place("SB_Vista", vistaGroup);
            SetupColliders(new[] { vroot.gameObject });
            PlaceVistaRecliners(vistaGroup);
            MarkStatic(vroot, false); RealtimeOnly(vistaGroup);
            Log("vista pieces added to the open scene (it predated the vista layout)");
        }
        ApplySeating(vista);
        EditorSceneManager.MarkSceneDirty(scene);
        Debug.Log("[Sphererebro] seating preview (scene NOT saved)\n" + Report);
    }

    static Vector3 Polar(float r, float phiDeg, float y)
    {
        var a = phiDeg * Mathf.Deg2Rad;
        return new Vector3(r * Mathf.Sin(a), y, r * Mathf.Cos(a));
    }

    // Banter seat, as the Polys loveseats: the player sits at the object facing its forward; clicked via a UI-layer trigger.
    static GameObject AddSeat(Transform parent, string name, Vector3 localPos, Quaternion localRot, Vector3 clickCenter, Vector3 clickSize)
    {
        var seat = new GameObject(name) { layer = UI };
        seat.transform.SetParent(parent, false);
        seat.transform.localPosition = localPos; seat.transform.localRotation = localRot;
        var click = seat.AddComponent<BoxCollider>(); click.isTrigger = true; click.center = clickCenter; click.size = clickSize;
        ObjectId(seat);
        var attached = seat.GetComponent<BS.BSAttachedObject>();
        if (attached == null) attached = seat.AddComponent<BS.BSAttachedObject>();
        if (seat.GetComponent<BS.BSSeat>() == null) seat.AddComponent<BS.BSSeat>();
        var so = new SerializedObject(attached);
        so.FindProperty("attachmentType").intValue = (int)BS.AttachmentType.Physics;
        so.FindProperty("avatarAttachmentType").intValue = (int)BS.AvatarAttachmentType.AvatarAttachTo;
        so.FindProperty("jointAvatar").boolValue = true;
        so.FindProperty("isSeat").boolValue = true;
        so.FindProperty("autoAttach").boolValue = false;
        so.FindProperty("unseatOnMove").boolValue = true;
        so.FindProperty("unseatOnJump").boolValue = true;
        so.ApplyModifiedPropertiesWithoutUndo();
        return seat;
    }

    // ---- desk: buttons (UI layer, clickable), labels, status text, joystick ---------------------------------------------------
    public static readonly Dictionary<string, string> ButtonLabels = new Dictionary<string, string>
    {
        ["RotL"] = "TURN\nLEFT", ["RotStop"] = "STOP", ["RotR"] = "TURN\nRIGHT", ["Home"] = "HOME",
        ["Bridge"] = "BRIDGE", ["Drawspan"] = "DRAW\nSPAN", ["House"] = "HOUSE\nLIGHTS", ["XRTM"] = "XR TIME\nMACHINE",
        ["SphereDark"] = "DARK", ["SpherePanels"] = "PANELS", ["SphereLattice"] = "LATTICE", ["SphereVideo"] = "VIDEO",
        ["Ride"] = "RIDE", ["Lights"] = "LIGHTS", ["Show"] = "IPN\nCUBE",
    };

    // the desk top's slope (Blender: atan2(1.08 - 0.95, 0.95 - 0.62)) and the key height (KEY_H): the legends sit on the keys
    const float DeskSlope = 21.5f, KeyHeight = 0.007f;
    static void SetupDesk(Transform stage)
    {
        var font = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>("Assets/TextMesh Pro/Resources/Fonts & Materials/LiberationSans SDF.asset");
        var desk = Find(stage, "Desk_Body");
        foreach (var t in All(stage).Where(t => t.name.StartsWith("Desk_Btn_")).ToList())
        {
            t.gameObject.layer = UI;
            var b = t.gameObject.AddComponent<BoxCollider>();
            var bounds = t.GetComponent<MeshFilter>().sharedMesh.bounds;
            b.center = bounds.center + new Vector3(0, 0.01f, 0); b.size = bounds.size + new Vector3(0.02f, 0.03f, 0.02f);
            ObjectId(t.gameObject);
            // the legend is printed INTO the key face (a texture, SB_KeyFace; the Blender generator renders and maps it):
            // no floating text over the keys any more (Ben, 2026-11-07)
        }
        // status line: NOT shown any more (Ben, 2026-11-07: "text over dash is a no-no"). The object stays, with its BS Text,
        // so the script keeps one place to write its messages, but it draws nothing (renderer off, fully transparent). The
        // discreet admin-only notification panel (like the Polys console) replaces it later; the script also logs each one.
        var status = new GameObject("Desk_Status");
        status.transform.SetParent(desk, false);
        status.transform.localPosition = new Vector3(0, 0.5f, 0f);
        var st = Tmp(status, font, "", 0.5f, new Vector2(0.9f, 0.12f));
        st.color = new Color(0.55f, 0.85f, 1f, 0f);
        var smr = status.GetComponent<MeshRenderer>(); if (smr != null) smr.enabled = false;
        ObjectId(status);
        status.AddComponent<BS.BSText>();
        // XR Time Machine, built into the desk (Ben, 2026-11-07: it opened stuck in the floor). The plugin builds its panel
        // on this mount (XRTM_CONFIG.ui.anchor in script.js): straight ahead above the desk's outer edge, leaning back 20 deg,
        // facing the presenter, turning with the dais. 0.34 x 0.58 m when open; only owners and moderators get it, on their
        // own device, so the audience never sees it.
        var mount = new GameObject("Desk_XRTM_Mount");
        mount.transform.SetParent(desk, false);
        mount.transform.localPosition = new Vector3(0, 1.42f, 0.98f);   // lower edge ~1.15 m: clear of the joystick below it
        mount.transform.localRotation = Quaternion.Euler(20f, 0, 0);
        ObjectId(mount);
        // the VIDEO submenu (2026-11-07): the script builds a small panel here when VIDEO is pressed (presenter's own device),
        // to the right of straight ahead, above the desk's edge, leaning back and facing the presenter
        var vmount = new GameObject("Desk_Video_Mount");
        vmount.transform.SetParent(desk, false);
        var vf = new Vector3(Mathf.Sin(40f * Mathf.Deg2Rad), 0, Mathf.Cos(40f * Mathf.Deg2Rad));
        vmount.transform.localPosition = vf * 0.98f + Vector3.up * 1.28f;
        vmount.transform.localRotation = Quaternion.LookRotation(vf, Vector3.up) * Quaternion.Euler(20f, 0, 0);
        ObjectId(vmount);
        // The joystick (2026-11-07, Ben: the fist moved opposite to his hand; it should follow the avatar hand, and ideally
        // be invisible when it works). The SDK holds a grabbed object with a PHYSICS hand jointed to it; a stick that is
        // physically held in place pushes that hand the other way. So the hand grabs an INVISIBLE grip, a trigger capsule
        // round the knob, with nothing holding it: the fist follows the real hand exactly. The world script reads the
        // hand's tilt and twist relative to how it was first grabbed (tilt forward = drive, sideways = slide, twist =
        // rotate) and leans the VISIBLE stick to show it. The grip is kinematic (riding the dais) until grabbed, free while
        // held, and snaps back to the knob on release.
        var stick = Find(stage, "Desk_Joystick");          // the visible stick: shows the deflection, never grabbed
        ObjectId(stick.gameObject);
        var grip = new GameObject("Desk_Joystick_Grip") { layer = Grabbable };
        grip.transform.SetParent(stick.parent, false);
        grip.transform.localPosition = stick.localPosition + Vector3.up * 0.165f;   // round the knob
        var cap = grip.AddComponent<CapsuleCollider>(); cap.isTrigger = true; cap.radius = 0.05f; cap.height = 0.14f; cap.direction = 1;
        var rb = grip.AddComponent<Rigidbody>();
        rb.useGravity = false; rb.isKinematic = true; rb.mass = 0.2f; rb.linearDamping = 2f; rb.angularDamping = 2f;
        rb.interpolation = RigidbodyInterpolation.Interpolate;
        // Cylinder grip (SDK grab presets: "Cylinder (Stick)"): held from whatever side the hand comes
        var sgr = grip.AddComponent<BS.BSGrababble>();
        var sgo = new SerializedObject(sgr);
        var sgt = sgo.FindProperty("grabType"); if (sgt != null) sgt.intValue = (int)BSGrabType.Cylinder;
        var sgrad = sgo.FindProperty("grabRadius"); if (sgrad != null) sgrad.floatValue = 0.02f;
        sgo.ApplyModifiedPropertiesWithoutUndo();
        grip.AddComponent<BS.BSWorldObject>();
        ObjectId(grip);
        ObjectId(Find(stage, "Desk_Joystick_Base").gameObject);
        Log("desk: " + All(stage).Count(t => t.name.StartsWith("Desk_Btn_")) + " buttons");
    }

    static TextMeshPro Tmp(GameObject g, TMP_FontAsset font, string text, float size, Vector2 box)
    {
        var tmp = g.AddComponent<TextMeshPro>();
        if (font != null) tmp.font = font;
        tmp.text = text; tmp.fontSize = size; tmp.alignment = TextAlignmentOptions.Center;
        tmp.textWrappingMode = TextWrappingModes.NoWrap; tmp.overflowMode = TextOverflowModes.Overflow;
        tmp.rectTransform.sizeDelta = box;
        var mr = g.GetComponent<MeshRenderer>(); if (mr != null) mr.shadowCastingMode = ShadowCastingMode.Off;
        return tmp;
    }

    // ---- riding the dais: the SDK has no moving-platform support for a standing player (spec 2.5) ------------------------
    // Plan A: a BS Attached Object on the dais itself with AvatarAttachTo (the player goes on the object, held by a joint,
    // like a vehicle); the RIDE key attaches/detaches the local player. Not a seat, so they stand. Pushing the move stick
    // releases them (unseatOnMove), so nobody is ever stuck. Plan B: two perches on the dais are real seats, which the SDK
    // documents riding a kinematic body. Both need the headset test (spike S1).
    static void SetupRide(Transform stage)
    {
        // RIDE is gone (Ben, 2026-11-07: "a mess... a failure"): no Attached Object on the dais and no zone trigger. The
        // stools on the dais are gone too (Ben: "no stools, remove them"): switched off by RetireRemoved. People stand on
        // the platform, as many as fit; the world script moves the dais physically and keeps standing players with it.
        Log("dais: no RIDE, no stools (standing players are kept with it by the world script)");
    }

    // ---- the bar stools are seats (2026-11-07, Ben: "the ones in the lounge don't have seats"): the player sits on top
    // (0.82 m, the cushion), facing the bar counter (outward, away from the sphere), clicked like the recliners
    static void SeatBarStools(Transform band)
    {
        int n = 0;
        foreach (var s in All(band).Where(t => t.name.StartsWith("Band_BarStool_")).ToList())
        {
            var outward = new Vector3(s.position.x, 0, s.position.z).normalized;
            var face = Quaternion.Inverse(s.rotation) * Quaternion.LookRotation(outward, Vector3.up);
            var seat = AddSeat(s, "Seat", new Vector3(0, 0.82f, 0), face, new Vector3(0, -0.1f, 0), new Vector3(0.45f, 0.35f, 0.45f));
            // the kinematic body BSSeat would add at runtime, added here: it also keeps MarkStatic (baked concourse) off it
            var srb = seat.AddComponent<Rigidbody>(); srb.isKinematic = true; srb.useGravity = false;
            n++;
        }
        Log($"bar stools: {n} seats, facing the counter");
    }

    // ---- grabbable glasses and bottles (Polys GrabLite spec), each with a Home the script returns it to ------------------------
    static void PlaceProps(Transform band, Transform props)
    {
        var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SB_Props.fbx");
        // stemless wine glasses (2026-11-07) in place of the flutes: they fit the recliner drink holders
        var flute = model.GetComponentsInChildren<MeshFilter>(true).First(m => m.name == "Prop_StemlessGlass");
        var bottle = model.GetComponentsInChildren<MeshFilter>(true).First(m => m.name == "Prop_BeerBottle");
        int nf = 0, nb = 0;
        void Make(MeshFilter src, Vector3 pos, float yaw, float mass)
        {
            bool isFlute = src == flute;
            var name = isFlute ? $"Wine Glass {++nf:00}" : $"Beer Bottle {++nb:00}";
            var go = new GameObject(name) { layer = Grabbable };
            go.transform.SetParent(props, false);
            go.transform.position = pos; go.transform.rotation = Quaternion.Euler(0, yaw, 0);
            go.AddComponent<MeshFilter>().sharedMesh = src.sharedMesh;
            var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = src.GetComponent<MeshRenderer>().sharedMaterials;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            var mc = go.AddComponent<MeshCollider>(); mc.sharedMesh = src.sharedMesh; mc.convex = true;
            var rb = go.AddComponent<Rigidbody>(); rb.mass = mass; rb.interpolation = RigidbodyInterpolation.Interpolate;
            rb.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            var gr = go.AddComponent<BS.BSGrababble>();
            var so = new SerializedObject(gr);
            // SOFT grip: the hand takes hold wherever it touches, and the glass or bottle keeps the angle it had in the hand, so
            // it follows the wrist exactly. (2026-11-07, Ben with a beer bottle: Point snapped the hand into one fixed pose and
            // faced it wrong; Cylinder re-aims the hand onto the axis, with the SDK's fixed 40 deg tilt and an upright flip,
            // and bending the wrist moved the bottle the opposite way.)
            var gt = so.FindProperty("grabType"); if (gt != null) gt.intValue = (int)BSGrabType.Soft;
            var rad = so.FindProperty("grabRadius"); if (rad != null) rad.floatValue = 0.01f;
            so.ApplyModifiedPropertiesWithoutUndo();
            go.AddComponent<BS.BSSyncedObject>();
            go.AddComponent<BS.BSWorldObject>();
            ObjectId(go);
            var home = new GameObject(name + " Home");
            home.transform.SetParent(props, false); home.transform.position = pos; home.transform.rotation = go.transform.rotation;
            ObjectId(home);
        }
        // grips: glass 5 cm above its base, bottle 12 cm above its base
        foreach (var table in All(band).Where(t => t.name.StartsWith("Band_StandingTable_")).OrderBy(t => t.name))
        {
            var top = table.position + Vector3.up * 1.1f;
            Make(flute, top + new Vector3(0.12f, 0.051f, 0.08f), 0, 0.25f);
            Make(flute, top + new Vector3(-0.13f, 0.051f, 0.05f), 40, 0.25f);
            Make(bottle, top + new Vector3(0.02f, 0.121f, -0.15f), 0, 0.4f);
        }
        var cc = D.concourse;
        float barR = cc.barFaceR + 0.42f, span = cc.barPhi1 - cc.barPhi0;
        for (int i = 0; i < 6; i++)
        {
            float phi = cc.barPhi0 + 3f + i * (span - 6f) / 5f;
            Make(flute, Polar(barR, phi, cc.barTopY + 0.051f), 0, 0.25f);
            Make(bottle, Polar(barR, phi + 1.6f * 59.62f / barR, cc.barTopY + 0.121f), 0, 0.4f);
        }
        Log($"props: {nf} stemless glasses, {nb} bottles (each with a Home)");
    }

    // ---- escalator steps: an Animator slides the step strip up one step and loops (the ramp collider does the carrying) -----
    static void SetupEscalator(Transform plaza)
    {
        var steps = Find(plaza, "Esc_Steps");
        var pitch = V(D.escalator.stepPitch);
        var p0 = steps.localPosition;
        var clip = new AnimationClip { name = "Esc_Steps_Loop", frameRate = 30 };
        var settings = AnimationUtility.GetAnimationClipSettings(clip); settings.loopTime = true;
        AnimationUtility.SetAnimationClipSettings(clip, settings);
        clip.SetCurve("", typeof(Transform), "localPosition.x", AnimationCurve.Linear(0, p0.x, 0.9f, p0.x));
        clip.SetCurve("", typeof(Transform), "localPosition.y", AnimationCurve.Linear(0, p0.y, 0.9f, p0.y + pitch.y));
        clip.SetCurve("", typeof(Transform), "localPosition.z", AnimationCurve.Linear(0, p0.z, 0.9f, p0.z + pitch.z));
        var clipPath = Root + "/Animation/Esc_Steps_Loop.anim";
        AssetDatabase.DeleteAsset(clipPath); AssetDatabase.CreateAsset(clip, clipPath);
        var ctrlPath = Root + "/Animation/Esc_Steps.controller";
        AssetDatabase.DeleteAsset(ctrlPath);
        var ctrl = AnimatorController.CreateAnimatorControllerAtPathWithClip(ctrlPath, clip);
        var anim = steps.gameObject.AddComponent<Animator>(); anim.runtimeAnimatorController = ctrl;
        anim.cullingMode = AnimatorCullingMode.CullCompletely;

        // The ride (2026-11-07, Ben: "get on the escalator and have it carry you up"). The SDK has no moving platform for a
        // standing player, so: step into the trigger at the foot and the world script puts you ON a carriage (BS Attached
        // Object, AvatarAttachTo, like a vehicle: the same mechanism as RIDE on the dais) and glides it up the slope by
        // setting its Rigidbody velocity (smooth at the frame rate, not stepped by the script), then lets you off at the
        // top. Push the stick to step off any time. Each player rides their own copy (it isn't synced); others see the
        // rider's avatar move. Fallback if attaching isn't available: a teleport to the top. Headset test pending.
        if (D.escalator.foot == null || D.escalator.top == null) { Log("escalator ride: no foot/top in derived.json"); return; }
        Vector3 foot = V(D.escalator.foot), top = V(D.escalator.top);
        var car = new GameObject("Esc_Carriage");
        car.transform.SetParent(plaza, false);
        car.transform.SetPositionAndRotation(foot, Quaternion.LookRotation(new Vector3(top.x - foot.x, 0, top.z - foot.z).normalized, Vector3.up));
        var crb = car.AddComponent<Rigidbody>();
        crb.useGravity = false; crb.isKinematic = false; crb.mass = 500f; crb.linearDamping = 0f; crb.angularDamping = 0f;
        crb.constraints = RigidbodyConstraints.FreezeRotation; crb.interpolation = RigidbodyInterpolation.Interpolate;
        var att = car.AddComponent<BS.BSAttachedObject>();
        var aso = new SerializedObject(att);
        aso.FindProperty("attachmentType").intValue = (int)BS.AttachmentType.Physics;
        aso.FindProperty("avatarAttachmentType").intValue = (int)BS.AvatarAttachmentType.AvatarAttachTo;
        aso.FindProperty("jointAvatar").boolValue = true;
        aso.FindProperty("isSeat").boolValue = false;
        aso.FindProperty("autoAttach").boolValue = false;
        aso.FindProperty("unseatOnMove").boolValue = true;
        aso.FindProperty("unseatOnJump").boolValue = true;
        aso.ApplyModifiedPropertiesWithoutUndo();
        ObjectId(car);
        var trig = new GameObject("Esc_Foot_TRIG") { layer = 2 };   // Ignore Raycast: a trigger, not a wall, out of the way of clicks
        trig.transform.SetParent(plaza, false);
        trig.transform.SetPositionAndRotation(foot + Vector3.up * 0.9f, car.transform.rotation);
        var tc = trig.AddComponent<BoxCollider>(); tc.isTrigger = true; tc.size = new Vector3(1.1f, 1.8f, 0.9f);
        trig.AddComponent<BS.BSColliderEvents>();
        ObjectId(trig);
        Log($"escalator ride: carriage {foot} -> {top}, {Vector3.Distance(foot, top):0.0} m");
    }

    // ---- spawn, teleports, rescue ---------------------------------------------------------------------------------------------
    static Transform Dest(Transform parent, string name, Vector3 pos, float yaw)
    {
        var go = new GameObject(name); go.transform.SetParent(parent, false);
        go.transform.position = pos; go.transform.rotation = Quaternion.Euler(0, yaw, 0);
        ObjectId(go); return go.transform;
    }

    static void Teleporter(Transform parent, string name, Vector3 pos, Vector3 size, Transform dest)
    {
        var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.position = pos;
        var bc = go.AddComponent<BoxCollider>(); bc.isTrigger = true; bc.size = size;
        ObjectId(go);
        var tp = go.AddComponent<BS.BSTeleporter>();
        var so = new SerializedObject(tp); so.FindProperty("destination").objectReferenceValue = dest; so.ApplyModifiedPropertiesWithoutUndo();
    }

    static void SetupNavigation(Transform nav, Transform safety, Transform plaza)
    {
        var spawn = Dest(nav, "Nav_Spawn", V(D.nav.spawn), 0);
        var sp = spawn.gameObject.AddComponent<BS.BSSpawn>();
        var so = new SerializedObject(sp); var r = so.FindProperty("radius"); if (r != null) { r.floatValue = 1.5f; so.ApplyModifiedPropertiesWithoutUndo(); }
        var band = Dest(nav, "Nav_BandArrival", V(D.nav.bandArrival), 0);
        // in vista the "ring" destination (where rescue lands) is the top of the vista aisle, facing the dome
        var ring = Dest(nav, "Nav_RingDest", V(Vista ? D.vista.landing : D.nav.ringDest), 0);
        Dest(nav, "Nav_DaisDest", V(Vista ? D.vista.daisDest : D.nav.daisDest), 0);
        var pad = Find(plaza, "Plaza_Lift_Pad_EMIT");
        Teleporter(nav, "Plaza_Lift_TRIG", pad.position + Vector3.up * 1f, new Vector3(1.6f, 2f, 1.6f), band);
        // anyone who falls into the sphere comes back to the ring landing before reaching the bottom
        Teleporter(safety, "Sphere_Rescue_TRIG", new Vector3(0, D.rescue.y, 0), V(D.rescue.size), ring);
    }

    // ---- lighting: concourse and plaza baked and warm; the sphere real-time only, so it can go pitch dark -------------------
    static Light AddLight(Transform parent, string name, LightType type, Vector3 pos, Quaternion rot, Color c, float intensity, float range, LightmapBakeType mode, float spot = 60f)
    {
        var go = new GameObject(name); go.transform.SetParent(parent, false); go.transform.position = pos; go.transform.rotation = rot;
        var l = go.AddComponent<Light>(); l.type = type; l.color = c; l.intensity = intensity; l.range = range; l.lightmapBakeType = mode;
        l.shadows = LightShadows.None; if (type == LightType.Spot) { l.spotAngle = spot; l.innerSpotAngle = spot * 0.6f; }
        return l;
    }

    // Brightness, 2026-11-06 walkthrough: "too dark, everywhere". Baked lights x2.5 and lighter ceiling/floor; the sphere's
    // real-time key and house lights brighter and ON at load (House preset). Lights Out is a preset, not the default.
    const float BakedGain = 3.5f;   // 2.5 -> 3.5 (2026-11-07): the softer fittings and matt floor bounce less light
    static void SetupLighting(Transform lighting, Transform band, Transform plaza)
    {
        var warm = new Color(1f, 0.76f, 0.5f); var amber = new Color(1f, 0.62f, 0.32f); var cool = new Color(0.55f, 0.75f, 1f);
        var cc = D.concourse; var g = BakedGain;
        // 2026-11-07, Ben: the ring and hanging lights were too hot. Pendants and coves come down; the light that's lost comes
        // back softer from the up-light sconces washing the walls; coves, sconces and lounge spots take the zone tints (club
        // look: rose at the restroom ends, amber at the bar, blue at the portal, violet in the lounges; no green). All
        // baked (SDK performance doc: "Bake your lighting"), so none of it costs a frame on Quest.
        var bandL = new GameObject("Concourse (baked)").transform; bandL.SetParent(lighting, false);
        foreach (var p in All(band).Where(t => t.name.StartsWith("Band_Pendant_")))
            AddLight(bandL, "Pendant " + p.name.Substring(12), LightType.Point, p.position + Vector3.down * 0.5f, Quaternion.identity, warm, 5f * g, 7f, LightmapBakeType.Baked);   // 7 -> 5: still glared over the bar
        int coves = Mathf.Max(2, Mathf.RoundToInt((cc.phi1 - cc.phi0 - 12f) / 12f));
        for (int i = 0; i <= coves; i++)
        {
            float phi = cc.phi0 + 6f + i * (cc.phi1 - cc.phi0 - 12f) / coves;
            if (Mathf.Abs(phi - 180f) < 4f) continue;
            var zc = Color.Lerp(ZoneAt(phi), amber, 0.25f);
            AddLight(bandL, $"Cove In {phi:000}", LightType.Point, Polar(cc.coveInR, phi, 3.9f), Quaternion.identity, zc, 8f * g, 10f, LightmapBakeType.Baked);
            AddLight(bandL, $"Cove Out {phi:000}", LightType.Point, Polar(cc.coveOutR, phi, 3.9f), Quaternion.identity, zc, 8f * g, 10f, LightmapBakeType.Baked);
        }
        foreach (var a in cc.loungePhis)
            AddLight(bandL, $"Lounge {a:000}", LightType.Spot, Polar(cc.loungeR, a, 4.3f), Quaternion.Euler(90, 0, 0), Color.Lerp(ZoneAt(a), warm, 0.4f), 12f * g, 10f, LightmapBakeType.Baked, 90f);
        int sconces = 0;
        foreach (var s in All(band).Where(t => t.name.StartsWith("Band_Sconce_")).ToList())
        {
            var parts = s.name.Split('_');   // Band_Sconce_<zone>_<nn>
            var c = ZoneColor.TryGetValue(parts.Length > 2 ? parts[2] : "", out var zc) ? zc : amber;
            var outward = new Vector3(s.position.x, 0, s.position.z).normalized;
            AddLight(bandL, "Sconce " + s.name.Substring(12), LightType.Spot, s.position + Vector3.up * 0.2f - outward * 0.12f,
                Quaternion.LookRotation(Vector3.up + outward * 0.25f), c, 12f * g, 6f, LightmapBakeType.Baked, 95f);
            sconces++;
        }
        Log($"concourse: {sconces} sconces, zones {(D.zones?.names == null ? "none" : string.Join("/", D.zones.names))}");
        var plazaL = new GameObject("Plaza (baked)").transform; plazaL.SetParent(lighting, false);
        foreach (var p in All(plaza).Where(t => t.name.StartsWith("Plaza_Planter_")))
            AddLight(plazaL, "Planter " + p.name.Substring(14), LightType.Point, p.position + Vector3.up * 2.8f, Quaternion.identity, warm, 12f * g, 13f, LightmapBakeType.Baked);
        AddLight(plazaL, "Facade Wash", LightType.Spot, V(D.plaza.facadeWash), Quaternion.LookRotation(new Vector3(0, 9f, 12f)), amber, 40f * g, 32f, LightmapBakeType.Baked, 70f);
        AddLight(plazaL, "Spawn Glow", LightType.Point, V(D.plaza.spawnGlow), Quaternion.identity, cool, 8f * g, 10f, LightmapBakeType.Baked);
        // sphere: real-time only. A BS Light on each makes it reachable from the script (lighting presets).
        var sphereL = new GameObject("Sphere (realtime)").transform; sphereL.SetParent(lighting, false);
        // same names in both layouts (the script finds them by name); in vista the key lights the presenter on the stage from
        // the dome side (the desk faces the dome) and the three house lights hang over the rows
        var kp = KeyPose(Vista);
        var key = AddLight(sphereL, "Dais Key", LightType.Spot, kp.pos, kp.rot, warm, 26f, 13f, LightmapBakeType.Realtime, 38f);
        key.renderMode = LightRenderMode.ForcePixel;   // "Important": never dropped to per-vertex or culled first (Quest: 4 a object)
        key.gameObject.AddComponent<BS.BSLight>(); ObjectId(key.gameObject);
        var house = new GameObject("House Lights").transform; house.SetParent(sphereL, false);
        ObjectId(house.gameObject);
        for (int i = 0; i < 3; i++)
        {
            var hp = HousePose(Vista, i);
            var l = AddLight(house, $"House {i + 1}", LightType.Spot, hp.pos, hp.rot, amber, 30f, 16f, LightmapBakeType.Realtime, 130f);
            l.renderMode = LightRenderMode.ForcePixel;
            l.gameObject.AddComponent<BS.BSLight>(); ObjectId(l.gameObject);
        }
        // reflection probes (baked) for the polished concourse and plaza
        float pr = cc.reflectionProbeR;
        foreach (var (name, pos, size) in new[] { ("Probe Bar", Polar(pr, (cc.barPhi0 + cc.barPhi1) / 2f, 2f), V(cc.reflectionProbeSize)),
                                                  ("Probe Portal", Polar(pr, 180f, 2f), V(cc.reflectionProbeSize) - new Vector3(6f, 0, 0)),
                                                  ("Probe Lounge", Polar(pr, cc.loungePhis[1], 2f), V(cc.reflectionProbeSize)),
                                                  ("Probe Plaza", V(D.plaza.center) + new Vector3(0, 2f, 0), new Vector3(2 * D.plaza.radius + 2, 10f, 2 * D.plaza.radius + 2)) })
        {
            var go = new GameObject(name); go.transform.SetParent(lighting, false); go.transform.position = pos;
            var rp = go.AddComponent<ReflectionProbe>(); rp.mode = ReflectionProbeMode.Baked; rp.size = size; rp.boxProjection = true;
            rp.resolution = 128; rp.importance = 1;
        }
        // light probes over the concourse and plaza (props and seats pick up the baked light from these)
        var lp = new GameObject("Light Probes").AddComponent<LightProbeGroup>(); lp.transform.SetParent(lighting, false);
        var pts = new List<Vector3>();
        for (float phi = cc.phi0 + 4f; phi <= cc.phi1 - 4f; phi += 6f)
            foreach (var rr in cc.probeRadii) foreach (var yy in new[] { 0.5f, 2.5f }) pts.Add(Polar(rr, phi, yy));
        var pc = V(D.plaza.center); float step = D.plaza.radius * 0.375f;
        for (int x = -2; x <= 2; x++) for (int z = -2; z <= 2; z++) foreach (var yy in new[] { 0.5f, 3f }) pts.Add(pc + new Vector3(x * step, yy, z * step));
        lp.probePositions = pts.ToArray();
        Log($"lights: {UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None).Length}, light probes {pts.Count}, baked gain x{BakedGain}");
    }
    static void MarkStatic(Transform root, bool gi, string keepMoving = null)
    {
        var moving = keepMoving == null ? null : Find(root, keepMoving);
        foreach (var t in All(root))
        {
            if (moving != null && (t == moving || t.IsChildOf(moving))) continue;
            if (t.GetComponent<Animator>() != null || t.GetComponent<Rigidbody>() != null) continue;
            var f = StaticEditorFlags.BatchingStatic | StaticEditorFlags.OccluderStatic | StaticEditorFlags.OccludeeStatic;
            if (gi) f |= StaticEditorFlags.ContributeGI | StaticEditorFlags.ReflectionProbeStatic;
            GameObjectUtility.SetStaticEditorFlags(t.gameObject, f);
            var mr = t.GetComponent<MeshRenderer>();
            if (mr != null && gi) mr.receiveGI = ReceiveGI.Lightmaps;
        }
    }

    // Inside the sphere everything is lit in real time only. Light probes would extrapolate the warm baked concourse onto
    // the dome, ring and seats (seen 2026-11-06: the whole interior glowed brown); off, the ambient is near black.
    static void RealtimeOnly(Transform root)
    {
        foreach (var r in root.GetComponentsInChildren<Renderer>(true))
        {
            r.lightProbeUsage = LightProbeUsage.Off;
            r.reflectionProbeUsage = ReflectionProbeUsage.Off;
        }
    }
    static void RenderSettingsSetup(Dictionary<string, Material> mats)
    {
        RenderSettings.skybox = mats["SB_Skybox"];
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.012f, 0.012f, 0.018f);
        RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
        RenderSettings.reflectionIntensity = 0.2f;
        RenderSettings.fog = false;
        var lsPath = Root + "/Settings/Sphererebro Lighting.lighting";
        var ls = AssetDatabase.LoadAssetAtPath<LightingSettings>(lsPath);
        if (ls == null) { ls = new LightingSettings(); AssetDatabase.CreateAsset(ls, lsPath); }
        ls.bakedGI = true; ls.realtimeGI = false;
        ls.lightmapper = LightingSettings.Lightmapper.ProgressiveGPU;
        ls.lightmapResolution = 8f; ls.lightmapMaxSize = 1024; ls.lightmapPadding = 2;
        ls.directionalityMode = LightmapsMode.NonDirectional;
        ls.mixedBakeMode = MixedLightingMode.Subtractive;
        ls.ao = true; ls.aoMaxDistance = 0.6f;
        ls.lightmapCompression = LightmapCompression.NormalQuality;
        ls.directSampleCount = 32; ls.indirectSampleCount = 256; ls.maxBounces = 2;
        ls.indirectScale = 1.4f;   // more bounce: the concourse read too dark on 2026-11-06
        Lightmapping.lightingSettings = ls;
        EditorUtility.SetDirty(ls);
    }

    static void Stats(GameObject[] roots)
    {
        int tris = 0, renderers = 0;
        foreach (var mf in roots.SelectMany(r => r.GetComponentsInChildren<MeshFilter>(true)))
        {
            var mr = mf.GetComponent<MeshRenderer>(); if (mr == null || mf.sharedMesh == null) continue;
            renderers++; for (int s = 0; s < mf.sharedMesh.subMeshCount; s++) tris += (int)mf.sharedMesh.GetIndexCount(s) / 3;
        }
        Log($"renderers {renderers}, triangles {tris} (all objects, incl. inactive)");
        Log("object ids: " + roots.SelectMany(r => r.GetComponentsInChildren<BS.BSObjectId>(true)).Count());
        Log(SphererebroMaterials.SkyFaceSize > 0 ? $"skybox: 8K cubemap, {SphererebroMaterials.SkyFaceSize} px faces (Quest ASTC 6x6 ~11 MB, PC BC7 ~25 MB, no mips)"
                                                 : "skybox: the old one (no Skybox/Sphererebro_Sky_8K file yet)");
    }
}
