using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

// Diagnostics for the talk build: what each named twin's renderers really are (active, layer, shader, colour, bounds).
// Automation request: "exec SphererebroTalkDiag.Run" -> Logs/talk_diag.txt. Changes nothing.
public static class SphererebroTalkDiag
{
    public static void Run()
    {
        var sb = new StringBuilder();
        var txt = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/_Sphererebro/Talk/Models/talk_text.fbx");
        if (txt != null)
            foreach (var t in txt.GetComponentsInChildren<Transform>(true).Take(6))
            {
                var mf = t.GetComponent<MeshFilter>();
                sb.AppendLine($"talk_text/{t.name}: lp {t.localPosition} ls {t.localScale} lr {t.localEulerAngles} mesh {(mf ? mf.sharedMesh.bounds.ToString() : "-")}");
            }
        var talk = GameObject.Find("Talk");
        sb.AppendLine("Talk root: " + (talk ? talk.transform.position.ToString() : "MISSING"));
        foreach (var n in new[] { "Talk_label1_Hold", "Talk_label1_Play", "Talk_locked_Hold", "Talk_halls_Hold" })
        {
            var g = talk ? talk.transform.Find(n) : null;
            if (g == null) { sb.AppendLine(n + ": MISSING"); continue; }
            var rs = g.GetComponentsInChildren<Renderer>(true);
            sb.AppendLine($"{n}: active {g.gameObject.activeSelf}, renderers {rs.Length}");
            foreach (var r in rs.Where(x => !n.StartsWith("Talk_label1") || x.name == "M" || x.name == "LabelPanel").Take(6))
            {
                var m = r.sharedMaterial; var mf = r.GetComponent<MeshFilter>();
                var path = string.Join("/", r.GetComponentsInParent<Transform>(true).Reverse().Skip(2).Select(x => x.name));
                sb.AppendLine($"   {path}: activeInH {r.gameObject.activeInHierarchy} en {r.enabled} layer {r.gameObject.layer} shader {(m ? m.shader.name : "null")} q {(m ? m.renderQueue : 0)} " +
                              $"col {(m && m.HasProperty("_BaseColor") ? m.GetColor("_BaseColor").ToString() : "-")} tex {(m && m.HasProperty("_BaseMap") && m.GetTexture("_BaseMap") ? m.GetTexture("_BaseMap").name : "-")} " +
                              $"verts {(mf && mf.sharedMesh ? mf.sharedMesh.vertexCount : -1)} lossy {r.transform.lossyScale} boundsC {r.bounds.center} size {r.bounds.size}");
            }
        }
        File.WriteAllText("Logs/talk_diag.txt", sb.ToString());
    }
}
