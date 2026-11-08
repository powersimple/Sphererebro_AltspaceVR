using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using J = SphererebroTalkJson;

// Cue 2T, "200 Years of Media": the glowing ribbon (28 segments, switched on as the comet passes), decade ticks, the
// comet (a bright bead with a trail), the event cards (pre-rendered by tools/talk/make_cards.py into atlases:
// talk/gen/tl_cards_<n>.png + talk/gen/tl_cards.json) and the stems that join each card to its year on the ribbon.
public static class SphererebroTalkTimeline
{
    static Dictionary<string, object> cards;
    static readonly Dictionary<int, Material> cardMats = new Dictionary<int, Material>();

    public static void Make(Transform t, Dictionary<string, object> make, Dictionary<string, object> tl, Func<string, Material> mat)
    {
        var kind = J.S(make["timeline"]);
        if (kind == "ribbon") Ribbon(t, make, mat);
        else if (kind == "comet") Comet(t, mat);
        else if (kind == "card") Card(t, (int)J.F(make["card"]), J.S(make["kind"]), mat, make);
        else if (kind == "stem") Stem(t, J.Fa(make["from"]), J.Fa(make["to"]), mat);
    }

    static Vector3 Arc(Dictionary<string, object> m, float f, float dr = 0, float dy = 0)
    {
        var c = J.Fa(m["center"]); float r = J.F(m["radius"]) + dr;
        float a = Mathf.Deg2Rad * Mathf.Lerp(J.F(m["a0"]), J.F(m["a1"]), f);
        return new Vector3(c[0] + r * Mathf.Sin(a), Mathf.Lerp(J.F(m["h0"]), J.F(m["h1"]), f) + dy, c[2] + r * Mathf.Cos(a));
    }

    static void Ribbon(Transform t, Dictionary<string, object> m, Func<string, Material> mat)
    {
        int segs = (int)J.F(m["segments"], 28);
        const int sub = 10; const float half = 0.32f;
        for (int k = 0; k < segs; k++)
        {
            var v = new List<Vector3>(); var uv = new List<Vector2>(); var tri = new List<int>();
            for (int i = 0; i <= sub; i++)
            {
                float f = (k + i / (float)sub) / segs;
                v.Add(Arc(m, f, 0, -half)); v.Add(Arc(m, f, 0, half));
                uv.Add(new Vector2(f, 0)); uv.Add(new Vector2(f, 1));
                if (i > 0) { int b = v.Count - 4; tri.AddRange(new[] { b, b + 1, b + 2, b + 1, b + 3, b + 2 }); }
            }
            // decade ticks inside this segment
            var tv = new List<Vector3>(); var tt = new List<int>();
            var tickFs = J.Fa(J.G(m, "ticks")) ?? new float[0]; var bigs = new HashSet<float>(J.Fa(J.G(m, "bigTicks")) ?? new float[0]);
            foreach (var f in tickFs)
            {
                if (f < k / (float)segs || f >= (k + 1) / (float)segs) continue;
                bool big = bigs.Contains(f);
                var p = Arc(m, f, -0.03f); var d = Arc(m, Mathf.Min(1, f + 0.001f), -0.03f) - p; d.y = 0; d.Normalize();
                float w = big ? 0.09f : 0.05f, h = big ? 1.5f : 0.75f;
                int b = tv.Count;
                tv.Add(p - d * w - Vector3.up * h); tv.Add(p + d * w - Vector3.up * h); tv.Add(p + d * w + Vector3.up * h); tv.Add(p - d * w + Vector3.up * h);
                tt.AddRange(new[] { b, b + 1, b + 2, b, b + 2, b + 3, b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            var seg = new GameObject($"Seg{k:00}"); seg.transform.SetParent(t, false);
            var mesh = new Mesh(); mesh.SetVertices(v); mesh.SetUVs(0, uv); mesh.SetTriangles(tri, 0);
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            mesh = SphererebroTalk.Save(mesh, $"timeline_seg{k:00}");
            seg.AddComponent<MeshFilter>().sharedMesh = mesh;
            var mr = seg.AddComponent<MeshRenderer>(); mr.sharedMaterial = mat("TK_Ribbon");
            if (tv.Count > 0)
            {
                var ticks = new GameObject("Ticks"); ticks.transform.SetParent(seg.transform, false);
                var tm = new Mesh(); tm.SetVertices(tv); tm.SetTriangles(tt, 0); tm.RecalculateNormals(); tm.RecalculateBounds();
                tm = SphererebroTalk.Save(tm, $"timeline_ticks{k:00}");
                ticks.AddComponent<MeshFilter>().sharedMesh = tm; ticks.AddComponent<MeshRenderer>().sharedMaterial = mat("TK_RibbonTick");
            }
        }
    }

    static void Comet(Transform t, Func<string, Material> mat)
    {
        var bead = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        UnityEngine.Object.DestroyImmediate(bead.GetComponent<Collider>());
        bead.name = "Bead"; bead.transform.SetParent(t, false); bead.transform.localScale = Vector3.one * 0.7f;
        bead.GetComponent<MeshRenderer>().sharedMaterial = mat("TK_RibbonTick");
        var tr = t.gameObject.AddComponent<TrailRenderer>();
        tr.time = 2.2f; tr.minVertexDistance = 0.4f;
        tr.widthCurve = new AnimationCurve(new Keyframe(0, 0.9f), new Keyframe(1, 0f));
        var g = new Gradient();
        g.SetKeys(new[] { new GradientColorKey(new Color(1f, 0.9f, 0.7f), 0), new GradientColorKey(new Color(1f, 0.6f, 0.25f), 1) },
                  new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) });
        tr.colorGradient = g;
        tr.sharedMaterial = mat("TK_Comet");
        tr.shadowCastingMode = ShadowCastingMode.Off; tr.receiveShadows = false;
        tr.alignment = LineAlignment.View;
        var halo = new GameObject("Halo"); halo.transform.SetParent(t, false);
        var ps = halo.AddComponent<ParticleSystem>();
        var main = ps.main; main.loop = true; main.startLifetime = 1.6f; main.startSpeed = 0.3f; main.startSize = new ParticleSystem.MinMaxCurve(0.15f, 0.5f);
        main.maxParticles = 300; main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.startColor = new Color(1f, 0.85f, 0.6f, 1);
        var em = ps.emission; em.rateOverTime = 60;
        var sh = ps.shape; sh.shapeType = ParticleSystemShapeType.Sphere; sh.radius = 0.4f;
        var col = ps.colorOverLifetime; col.enabled = true;
        var cg = new Gradient(); cg.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(new Color(1, 0.6f, 0.3f), 1) },
            new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0, 1) });
        col.color = cg;
        halo.GetComponent<ParticleSystemRenderer>().sharedMaterial = mat("TK_Particle");
    }

    static Dictionary<string, object> Cards()
    {
        if (cards != null) return cards;
        var p = "talk/gen/tl_cards.json";
        cards = File.Exists(p) ? J.O(J.Parse(File.ReadAllText(p))) : new Dictionary<string, object>();
        return cards;
    }

    static Material CardMat(int atlas, Func<string, Material> mat)
    {
        if (cardMats.TryGetValue(atlas, out var m)) return m;
        var path = $"Assets/_Sphererebro/Talk/Materials/TK_Card_{atlas}.mat";
        var baseMat = mat("TK_Card");
        m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(baseMat); AssetDatabase.CreateAsset(m, path); }
        m.CopyPropertiesFromMaterial(baseMat); m.shader = baseMat.shader;
        m.SetTexture("_BaseMap", AssetDatabase.LoadAssetAtPath<Texture2D>($"Assets/_Sphererebro/Talk/Textures/gen_tl_cards_{atlas}.png"));
        m.renderQueue = baseMat.renderQueue;
        foreach (var kw in baseMat.shaderKeywords) m.EnableKeyword(kw);
        EditorUtility.SetDirty(m);
        cardMats[atlas] = m;
        return m;
    }

    static void Card(Transform t, int i, string kind, Func<string, Material> mat, Dictionary<string, object> make)
    {
        var list = J.L(J.G(Cards(), "cards"));
        var c = list?.Select(J.O).FirstOrDefault(x => (int)J.F(x["i"]) == i);
        if (c == null) { Debug.LogWarning($"[Talk] timeline card {i} has no image (run tools/talk/make_cards.py)"); return; }
        float w = J.F(J.G(make, "w"), J.F(c["w"])), h = J.F(J.G(make, "h"), J.F(c["h"]));
        float u0 = J.F(c["u0"]), v0 = J.F(c["v0"]), u1 = J.F(c["u1"]), v1 = J.F(c["v1"]);
        var mesh = new Mesh();
        mesh.vertices = new[] { new Vector3(-w / 2, -h / 2, 0), new Vector3(w / 2, -h / 2, 0), new Vector3(w / 2, h / 2, 0), new Vector3(-w / 2, h / 2, 0) };
        // the card faces -Z (toward the audience at yaw 0): the viewer's right is +X
        mesh.uv = new[] { new Vector2(u0, v0), new Vector2(u1, v0), new Vector2(u1, v1), new Vector2(u0, v1) };
        mesh.triangles = new[] { 0, 2, 1, 0, 3, 2 };
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        mesh = SphererebroTalk.Save(mesh, $"timeline_card{i:00}");
        t.gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
        t.gameObject.AddComponent<MeshRenderer>().sharedMaterial = CardMat((int)J.F(c["atlas"]), mat);
    }

    static void Stem(Transform t, float[] a, float[] b, Func<string, Material> mat)
    {
        var A = new Vector3(a[0], a[1], a[2]); var B = new Vector3(b[0], b[1], b[2]);
        var eye = new Vector3(0, -1, -43);
        var d = (B - A); var f = (eye - (A + B) / 2).normalized; var side = Vector3.Cross(d, f).normalized * 0.03f;
        var mesh = new Mesh();
        mesh.vertices = new[] { A - side, A + side, B + side, B - side };
        mesh.triangles = new[] { 0, 1, 2, 0, 2, 3, 0, 2, 1, 0, 3, 2 };
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        mesh = SphererebroTalk.Save(mesh, $"timeline_stem_{t.name}");
        t.gameObject.AddComponent<MeshFilter>().sharedMesh = mesh;
        t.gameObject.AddComponent<MeshRenderer>().sharedMaterial = mat("TK_RibbonTick");
    }
}
