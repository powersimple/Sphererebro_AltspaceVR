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
    [Serializable] public class DEsc { public float[] stepPitch; }
    // the vista layout (seats: flat [row, x, y, z, ...]; housePos: flat [x, y, z, ...]: JsonUtility reads no nested arrays)
    [Serializable] public class DVista { public float[] daisMount, landing, daisDest, keyPos, keyTarget, housePos, seats; public float stageY; public int seatCount; }
    [Serializable] public class Derived { public float sphereRadius, domeClipRadius; public DConcourse concourse; public DPlaza plaza; public DNav nav; public DBridge bridge; public DRescue rescue; public DEsc escalator; public string seating; public DVista vista; }
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

    static void Build(bool bake)
    {
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
        // SHOW stays as an empty group: the show system (spec phase 3) puts its anchors and assets there

        SetupColliders(scene.GetRootGameObjects());
        SetupSphere(sphere, mats);
        SetupBridge(bridge);
        SetupStage(stage);
        PlaceRecliners(groups["STAGE"]);
        PlaceVistaRecliners(groups["VISTA"]);
        SetupDesk(stage);
        SetupRide(stage);
        if (Vista) MoveDaisToVista(stage, groups["VISTA"]);
        PlaceProps(band, groups["PROPS"]);
        SetupEscalator(plaza);
        SetupNavigation(groups["NAVIGATION"], groups["SAFETY"], plaza);
        SetupLighting(groups["LIGHTING"], band, plaza);
        MarkStatic(band, true); MarkStatic(plaza, true);
        MarkStatic(sphere, false); MarkStatic(stage, false, "Dais_Floor_Rotating"); MarkStatic(vista, false);
        foreach (var z in new[] { sphere, stage, bridge, groups["STAGE"], groups["VISTA"] }) RealtimeOnly(z);
        RenderSettingsSetup(mats);
        WriteScriptDims();
        SwitchLayout(groups, stage, band);

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
        {
            var mi = (ModelImporter)AssetImporter.GetAtPath(path);
            if (mi == null) continue;
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
                go.AddComponent<MeshFilter>().sharedMesh = src.sharedMesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = srcMr.sharedMaterials;
                mr.shadowCastingMode = ShadowCastingMode.Off;
                var body = go.AddComponent<BoxCollider>(); body.center = new Vector3(0, 0.55f, 0.18f); body.size = new Vector3(0.86f, 1.1f, 0.6f);
                AddSeat(go.transform, "Seat", new Vector3(0, 0.46f, -0.02f), Quaternion.identity, new Vector3(0, 0.1f, 0.0f), new Vector3(0.62f, 0.56f, 0.9f));
            }
        }
        Log("recliners: 33 + 35");
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
            go.AddComponent<MeshFilter>().sharedMesh = src.sharedMesh;
            var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = srcMr.sharedMaterials;
            mr.shadowCastingMode = ShadowCastingMode.Off;
            var body = go.AddComponent<BoxCollider>(); body.center = new Vector3(0, 0.55f, 0.18f); body.size = new Vector3(0.86f, 1.1f, 0.6f);
            AddSeat(go.transform, "Seat", new Vector3(0, 0.46f, -0.02f), Quaternion.identity, new Vector3(0, 0.1f, 0.0f), new Vector3(0.62f, 0.56f, 0.9f));
            n++;
        }
        Log($"vista recliners: {n} in {perRow.Count} rows ({string.Join(", ", perRow.OrderBy(kv => kv.Key).Select(kv => kv.Value))})");
    }

    // The dais (floor, desk, buttons, joystick, perches, RIDE zone: all its children) moves onto the vista stage, under a
    // mount. At HOME (yaw 0) the desk faces the dome, like the audience (Ben, 2026-11-07), and its open side faces the aisle,
    // so the presenter walks straight in. TURN still works (kept for now; in VR the presenter can turn themselves). The
    // script turns the dais in its local frame exactly as before. Its walls and gate stay behind with the round theatre
    // (switched off): Ben, "remove the walls on the side of the dais". BRIDGE and DRAWSPAN have nothing to move here.
    static void MoveDaisToVista(Transform stage, Transform vistaGroup)
    {
        var dais = Find(stage, "Dais_Floor_Rotating");
        var mount = new GameObject("Vista_Dais_Mount").transform;
        mount.SetParent(vistaGroup, false);
        mount.position = V(D.vista.daisMount); mount.rotation = Quaternion.identity;   // HOME: the desk faces the dome
        dais.SetParent(mount, false);
        dais.localPosition = Vector3.zero; dais.localRotation = Quaternion.identity;
        foreach (var key in new[] { "Bridge", "Drawspan" })
        {
            var label = Find(dais, "Label_" + key);
            var tmp = label != null ? label.GetComponent<TextMeshPro>() : null;
            if (tmp != null) tmp.text = "—";
        }
        Log($"vista: dais moved to the stage at {mount.position} (desk facing the dome at HOME); BRIDGE/DRAWSPAN keys blanked");
    }

    // The layout that isn't live is kept, switched off (Ben: keep it, turn it off; never delete). In vista: the round
    // ring and its seats, the bridge, and the concourse portal gate (it only stands while the bridge is away; vista has
    // no bridge, the entry deck is always there). The script finds none of these in vista and doesn't look for them.
    static void SwitchLayout(Dictionary<string, Transform> groups, Transform stage, Transform band)
    {
        if (Vista)
        {
            stage.gameObject.SetActive(false);
            foreach (var t in groups["STAGE"].Cast<Transform>().Where(t => t.name.StartsWith("Recliners Row"))) t.gameObject.SetActive(false);
            groups["BRIDGE"].gameObject.SetActive(false);
            var gate = Find(band, "Band_Gate_COL"); if (gate != null) gate.gameObject.SetActive(false);
        }
        else groups["VISTA"].gameObject.SetActive(false);
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
        ["Ride"] = "RIDE", ["Lights"] = "LIGHTS",
    };

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
            var key = t.name.Substring("Desk_Btn_".Length);
            var label = new GameObject("Label_" + key);
            label.transform.SetParent(desk, false);   // desk and buttons share the dais frame (both at its origin)
            var p = t.localPosition; var flat = new Vector3(p.x, 0, p.z);
            label.transform.localPosition = p - flat.normalized * 0.065f + Vector3.up * 0.012f;
            label.transform.localRotation = Quaternion.LookRotation(flat.normalized, Vector3.up) * Quaternion.Euler(62f, 0, 0);
            var tmp = Tmp(label, font, ButtonLabels.TryGetValue(key, out var s) ? s : key, 0.18f, new Vector2(0.12f, 0.05f));
            tmp.color = new Color(1f, 0.85f, 0.6f);
        }
        // status line across the front of the desk, readable from the centre (BS Text so the script can change it)
        var status = new GameObject("Desk_Status");
        status.transform.SetParent(desk, false);
        status.transform.localPosition = new Vector3(0, 1.16f, 0.93f);
        status.transform.localRotation = Quaternion.Euler(-10f, 0, 0);
        var st = Tmp(status, font, "SPHEREREBRO", 0.5f, new Vector2(0.9f, 0.12f));
        st.color = new Color(0.55f, 0.85f, 1f);
        ObjectId(status);
        status.AddComponent<BS.BSText>();
        // joystick: grab it and push left/right to turn the dais; the script returns it to centre on release
        var stick = Find(stage, "Desk_Joystick");
        stick.gameObject.layer = Grabbable;
        ObjectId(stick.gameObject);
        var bc = stick.gameObject.AddComponent<BoxCollider>();
        var sb = stick.GetComponent<MeshFilter>().sharedMesh.bounds; bc.center = sb.center; bc.size = sb.size * 1.6f;
        var rb = stick.gameObject.AddComponent<Rigidbody>();
        rb.useGravity = false; rb.isKinematic = false; rb.linearDamping = 20f; rb.angularDamping = 20f;
        rb.constraints = RigidbodyConstraints.FreezePositionY | RigidbodyConstraints.FreezeRotation;
        stick.gameObject.AddComponent<BS.BSGrababble>();
        stick.gameObject.AddComponent<BS.BSWorldObject>();
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
        var dais = Find(stage, "Dais_Floor_Rotating");
        var ride = dais.gameObject.AddComponent<BS.BSAttachedObject>();
        var so = new SerializedObject(ride);
        so.FindProperty("attachmentType").intValue = (int)BS.AttachmentType.Physics;
        so.FindProperty("avatarAttachmentType").intValue = (int)BS.AvatarAttachmentType.AvatarAttachTo;
        so.FindProperty("jointAvatar").boolValue = true;
        so.FindProperty("isSeat").boolValue = false;
        so.FindProperty("autoAttach").boolValue = false;
        so.FindProperty("unseatOnMove").boolValue = true;
        so.FindProperty("unseatOnJump").boolValue = true;
        so.ApplyModifiedPropertiesWithoutUndo();
        // where the dais is: a trigger the local player's body fires (BS Collider Events), so RIDE only works for someone
        // standing on it (the desk keys are clickable from afar; RIDE must never pull a player in from the seats).
        // Layer 2 (Ignore Raycast): a trigger, not a wall, and out of the way of teleport arcs and clicks.
        var zone = new GameObject("Dais_Zone_TRIG") { layer = 2 };
        zone.transform.SetParent(dais, false);
        var zc = zone.AddComponent<CapsuleCollider>(); zc.isTrigger = true; zc.center = new Vector3(0, 1.1f, 0); zc.radius = 1.45f; zc.height = 2.6f;
        zone.AddComponent<BS.BSColliderEvents>();
        ObjectId(zone);
        int perches = 0;
        foreach (var tag in new[] { "L", "R" })
        {
            var p = Find(stage, "Dais_Perch_" + tag);
            if (p == null) continue;
            var body = p.gameObject.AddComponent<CapsuleCollider>(); body.center = new Vector3(0, 0.39f, 0); body.height = 0.78f; body.radius = 0.2f;
            AddSeat(p, "Seat", new Vector3(0, 0.78f, 0), Quaternion.identity, new Vector3(0, 0f, 0), new Vector3(0.5f, 0.3f, 0.5f));
            perches++;
        }
        Log($"ride: attached object on the dais, {perches} perches");
    }

    // ---- grabbable glasses and bottles (Polys GrabLite spec), each with a Home the script returns it to ------------------------
    static void PlaceProps(Transform band, Transform props)
    {
        var model = AssetDatabase.LoadAssetAtPath<GameObject>($"{Root}/Models/SB_Props.fbx");
        var flute = model.GetComponentsInChildren<MeshFilter>(true).First(m => m.name == "Prop_ChampagneFlute");
        var bottle = model.GetComponentsInChildren<MeshFilter>(true).First(m => m.name == "Prop_BeerBottle");
        int nf = 0, nb = 0;
        void Make(MeshFilter src, Vector3 pos, float yaw, float mass)
        {
            bool isFlute = src == flute;
            var name = isFlute ? $"Champagne Flute {++nf:00}" : $"Beer Bottle {++nb:00}";
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
            var gt = so.FindProperty("grabType"); if (gt != null) gt.intValue = 0;
            var rad = so.FindProperty("grabRadius"); if (rad != null) rad.floatValue = 0.01f;
            so.ApplyModifiedPropertiesWithoutUndo();
            go.AddComponent<BS.BSSyncedObject>();
            go.AddComponent<BS.BSWorldObject>();
            ObjectId(go);
            var home = new GameObject(name + " Home");
            home.transform.SetParent(props, false); home.transform.position = pos; home.transform.rotation = go.transform.rotation;
            ObjectId(home);
        }
        // grips: flute 7 cm above its foot, bottle 12 cm above its base
        foreach (var table in All(band).Where(t => t.name.StartsWith("Band_StandingTable_")).OrderBy(t => t.name))
        {
            var top = table.position + Vector3.up * 1.1f;
            Make(flute, top + new Vector3(0.12f, 0.071f, 0.08f), 0, 0.2f);
            Make(flute, top + new Vector3(-0.13f, 0.071f, 0.05f), 40, 0.2f);
            Make(bottle, top + new Vector3(0.02f, 0.121f, -0.15f), 0, 0.4f);
        }
        var cc = D.concourse;
        float barR = cc.barFaceR + 0.42f, span = cc.barPhi1 - cc.barPhi0;
        for (int i = 0; i < 6; i++)
        {
            float phi = cc.barPhi0 + 3f + i * (span - 6f) / 5f;
            Make(flute, Polar(barR, phi, cc.barTopY + 0.071f), 0, 0.2f);
            Make(bottle, Polar(barR, phi + 1.6f * 59.62f / barR, cc.barTopY + 0.121f), 0, 0.4f);
        }
        Log($"props: {nf} flutes, {nb} bottles (each with a Home)");
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
    const float BakedGain = 2.5f;
    static void SetupLighting(Transform lighting, Transform band, Transform plaza)
    {
        var warm = new Color(1f, 0.76f, 0.5f); var amber = new Color(1f, 0.62f, 0.32f); var cool = new Color(0.55f, 0.75f, 1f);
        var cc = D.concourse; var g = BakedGain;
        var bandL = new GameObject("Concourse (baked)").transform; bandL.SetParent(lighting, false);
        foreach (var p in All(band).Where(t => t.name.StartsWith("Band_Pendant_")))
            AddLight(bandL, "Pendant " + p.name.Substring(12), LightType.Point, p.position + Vector3.down * 0.5f, Quaternion.identity, warm, 12f * g, 7f, LightmapBakeType.Baked);
        int coves = Mathf.Max(2, Mathf.RoundToInt((cc.phi1 - cc.phi0 - 12f) / 12f));
        for (int i = 0; i <= coves; i++)
        {
            float phi = cc.phi0 + 6f + i * (cc.phi1 - cc.phi0 - 12f) / coves;
            if (Mathf.Abs(phi - 180f) < 4f) continue;
            AddLight(bandL, $"Cove In {phi:000}", LightType.Point, Polar(cc.coveInR, phi, 3.9f), Quaternion.identity, amber, 10f * g, 11f, LightmapBakeType.Baked);
            AddLight(bandL, $"Cove Out {phi:000}", LightType.Point, Polar(cc.coveOutR, phi, 3.9f), Quaternion.identity, amber, 10f * g, 11f, LightmapBakeType.Baked);
        }
        foreach (var a in cc.loungePhis)
            AddLight(bandL, $"Lounge {a:000}", LightType.Spot, Polar(cc.loungeR, a, 4.3f), Quaternion.Euler(90, 0, 0), warm, 16f * g, 10f, LightmapBakeType.Baked, 90f);
        var plazaL = new GameObject("Plaza (baked)").transform; plazaL.SetParent(lighting, false);
        foreach (var p in All(plaza).Where(t => t.name.StartsWith("Plaza_Planter_")))
            AddLight(plazaL, "Planter " + p.name.Substring(14), LightType.Point, p.position + Vector3.up * 2.8f, Quaternion.identity, warm, 12f * g, 13f, LightmapBakeType.Baked);
        AddLight(plazaL, "Facade Wash", LightType.Spot, V(D.plaza.facadeWash), Quaternion.LookRotation(new Vector3(0, 9f, 12f)), amber, 40f * g, 32f, LightmapBakeType.Baked, 70f);
        AddLight(plazaL, "Spawn Glow", LightType.Point, V(D.plaza.spawnGlow), Quaternion.identity, cool, 8f * g, 10f, LightmapBakeType.Baked);
        // sphere: real-time only. A BS Light on each makes it reachable from the script (lighting presets).
        var sphereL = new GameObject("Sphere (realtime)").transform; sphereL.SetParent(lighting, false);
        // same names in both layouts (the script finds them by name); in vista the key lights the presenter on the stage from
        // the dome side (the desk faces the dome) and the three house lights hang over the rows
        var keyPos = Vista ? V(D.vista.keyPos) : new Vector3(0, 7f, 0.8f);
        var keyRot = Vista ? Quaternion.LookRotation(V(D.vista.keyTarget) - keyPos) : Quaternion.LookRotation(new Vector3(0, -1f, -0.1f));
        var key = AddLight(sphereL, "Dais Key", LightType.Spot, keyPos, keyRot, warm, 26f, 13f, LightmapBakeType.Realtime, 38f);
        key.gameObject.AddComponent<BS.BSLight>(); ObjectId(key.gameObject);
        var house = new GameObject("House Lights").transform; house.SetParent(sphereL, false);
        ObjectId(house.gameObject);
        for (int i = 0; i < 3; i++)
        {
            var pos = Vista ? new Vector3(D.vista.housePos[3 * i], D.vista.housePos[3 * i + 1], D.vista.housePos[3 * i + 2]) : Polar(6.3f, 60f + 120f * i, 7f);
            var aim = Vista ? Vector3.down : new Vector3(0, -1f, 0) + new Vector3(pos.x, 0, pos.z).normalized * 0.15f;
            var l = AddLight(house, $"House {i + 1}", LightType.Spot, pos, Quaternion.LookRotation(aim, Vista ? Vector3.forward : Vector3.up), amber, 30f, 16f, LightmapBakeType.Realtime, 130f);
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
    }
}
