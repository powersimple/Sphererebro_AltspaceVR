using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using J = SphererebroTalkJson;

// Cue 3's feed wall: one sector of an arc of portrait tiles around the audience (built as three merged meshes: bodies,
// screens from the 4x2 feed_screens atlas, and play/heart icons). The tile pattern repeats every `period` rows, so the
// looping scroll (exactly period rows) never shows a jump.
public static class SphererebroTalkFeed
{
    public static void Sector(Transform t, Dictionary<string, object> make, Func<string, Material> mat, string elId)
    {
        float R = J.F(make["radius"]), a0 = J.F(make["a0"]), a1 = J.F(make["a1"]);
        float y0 = J.F(make["y0"]), y1 = J.F(make["y1"]);
        float tw = J.F(make["tileW"]), th = J.F(make["tileH"]), gw = J.F(make["gapW"]);
        int period = (int)J.F(make["period"], 3);
        const float rowH = 2.2f;                       // = the scroll loop's step (choreo: 2.2 * period)
        var rnd = new System.Random((int)J.F(make["seed"], 1));
        float pitch = tw + gw;
        float arcLen = Mathf.Deg2Rad * (a1 - a0) * R;
        int cols = Mathf.Max(1, Mathf.FloorToInt(arcLen / pitch));
        int rows = Mathf.CeilToInt((y1 - y0 + rowH * period) / rowH);
        // per (col, row % period): screen cell 0..7, icon 0 none / 1 play / 2 heart, a slight depth offset
        var body = new MeshB(); var scr = new MeshB(); var ico = new MeshB();
        var pattern = new (int cell, int icon, float depth)[cols, period];
        for (int c = 0; c < cols; c++)
            for (int p = 0; p < period; p++)
            {
                int cell = rnd.Next(8); double r = rnd.NextDouble();
                pattern[c, p] = (cell, r < 0.14 ? 1 : r < 0.3 ? 2 : 0, (float)rnd.NextDouble() * 0.6f);
            }
        for (int c = 0; c < cols; c++)
        {
            float ang = Mathf.Deg2Rad * (a0 + (a1 - a0) * (c + 0.5f) / cols);
            var radial = new Vector3(Mathf.Sin(ang), 0, Mathf.Cos(ang));
            var normal = -radial;                                        // faces the audience
            var right = Vector3.Cross(normal, Vector3.up).normalized;    // the viewer's right (Unity is left-handed)
            for (int r = 0; r < rows; r++)
            {
                var pat = pattern[c, r % period];
                float yc = y0 - rowH * period + r * rowH + th / 2;
                var centre = radial * (R + pat.depth) + Vector3.up * yc;
                body.Box(centre - normal * 0.03f, right, Vector3.up, normal, tw, th, 0.06f);
                var sc = centre + normal * 0.005f;
                float inset = 0.05f;
                int cell = pat.cell; float u0 = (cell % 4) / 4f, v0 = 1 - (cell / 4 + 1) / 2f;
                scr.Quad(sc, right, Vector3.up, tw - inset * 2, th - inset * 2, new Vector2(u0, v0), new Vector2(u0 + 0.25f, v0 + 0.5f));
                if (pat.icon > 0)
                {
                    var ic = sc + normal * 0.01f + (pat.icon == 2 ? right * (tw * 0.28f) + Vector3.up * (-th * 0.36f) : Vector3.zero);
                    float s = pat.icon == 1 ? tw * 0.42f : tw * 0.26f;
                    float iu = pat.icon == 1 ? 0 : 0.5f;
                    ico.Quad(ic, right, Vector3.up, s, s, new Vector2(iu, 0), new Vector2(iu + 0.5f, 1));
                }
            }
        }
        Add(t, "Bodies", body.Mesh(), mat("TK_TileBody"), elId);
        Add(t, "Screens", scr.Mesh(), mat("TK_TileScreen"), elId);
        Add(t, "Icons", ico.Mesh(), mat("TK_TileIcon"), elId);
    }

    static void Add(Transform t, string name, Mesh m, Material mat, string elId)
    {
        m = SphererebroTalk.Save(m, $"{elId}_{t.parent?.name}_{name}");
        var go = new GameObject(name); go.transform.SetParent(t, false);
        go.AddComponent<MeshFilter>().sharedMesh = m; go.AddComponent<MeshRenderer>().sharedMaterial = mat;
    }

    class MeshB
    {
        readonly List<Vector3> v = new List<Vector3>(); readonly List<Vector3> n = new List<Vector3>();
        readonly List<Vector2> uv = new List<Vector2>(); readonly List<int> tri = new List<int>();
        public void Quad(Vector3 c, Vector3 right, Vector3 up, float w, float h, Vector2 uv0, Vector2 uv1)
        {
            int b = v.Count; var nn = Vector3.Cross(right, up).normalized;
            // the viewer looks along -normal; with right = viewer's right the winding below faces the viewer
            v.Add(c - right * w / 2 - up * h / 2); v.Add(c + right * w / 2 - up * h / 2); v.Add(c + right * w / 2 + up * h / 2); v.Add(c - right * w / 2 + up * h / 2);
            uv.Add(new Vector2(uv0.x, uv0.y)); uv.Add(new Vector2(uv1.x, uv0.y)); uv.Add(new Vector2(uv1.x, uv1.y)); uv.Add(new Vector2(uv0.x, uv1.y));
            for (int i = 0; i < 4; i++) n.Add(-nn);
            tri.AddRange(new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
        }
        public void Box(Vector3 c, Vector3 right, Vector3 up, Vector3 normal, float w, float h, float d)
        {
            Quad(c + normal * d / 2, right, up, w, h, Vector2.zero, new Vector2(w, h));                 // front
            Quad(c + right * w / 2, -normal, up, d, h, Vector2.zero, new Vector2(d, h));                // right side
            Quad(c - right * w / 2, normal, up, d, h, Vector2.zero, new Vector2(d, h));                 // left side
            Quad(c + up * h / 2, right, normal, w, d, Vector2.zero, new Vector2(w, d));                 // top
            Quad(c - up * h / 2, right, -normal, w, d, Vector2.zero, new Vector2(w, d));                // bottom
        }
        public Mesh Mesh()
        {
            var m = new Mesh { indexFormat = IndexFormat.UInt32 };
            m.SetVertices(v); m.SetNormals(n); m.SetUVs(0, uv); m.SetTriangles(tri, 0); m.RecalculateBounds();
            return m;
        }
    }
}
