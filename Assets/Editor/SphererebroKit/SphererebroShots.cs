using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Renders review shots of the built scene to ../Assets/previews/unity_*.png (outside the project). Menu: Sphererebro > Review
// Shots; batch: -executeMethod SphererebroShots.Batch. The sphere is shown the way the script leaves it at load (dark mode:
// screen and glow off) plus house lights on; nothing is saved.
public static class SphererebroShots
{
    [MenuItem("Sphererebro/Review Shots")]
    public static void Menu() => Shoot();

    public static void Batch()
    {
        EditorSceneManager.OpenScene("Assets/_Sphererebro/Scenes/Sphererebro.unity");
        Shoot();
    }

    static void Shoot()
    {
        ShaderUtil.allowAsyncCompilation = false;   // else lightmapped variants aren't ready and baked light is missing
        var outDir = Path.GetFullPath(Path.Combine(Application.dataPath, "../../Assets/previews"));
        Directory.CreateDirectory(outDir);
        var screen = GameObject.Find("Sphere_Screen"); var glow = GameObject.Find("Sphere_Shell_Glow");
        var inner = GameObject.Find("Sphere_Shell_Inner"); var house = GameObject.Find("House Lights");
        screen.SetActive(false); glow.SetActive(false); house.SetActive(false);
        var go = new GameObject("ReviewCam");
        var cam = go.AddComponent<Camera>();
        cam.nearClipPlane = 0.05f; cam.farClipPlane = 1500f; cam.fieldOfView = 70f;
        // sRGB target: a linear one saved as PNG looks several stops darker than the editor (first shots, 2026-11-06)
        var rt = new RenderTexture(1600, 900, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB) { antiAliasing = 4 };
        cam.targetTexture = rt;
        Shot(cam, rt, outDir, "unity_01_plaza", new Vector3(-5f, -4.2f, -90f), new Vector3(0, 4f, -55f));
        Shot(cam, rt, outDir, "unity_02_bar", new Vector3(2f, 1.7f, -54f), new Vector3(20f, 1.4f, -56f));
        Shot(cam, rt, outDir, "unity_03_portal", new Vector3(0, 1.7f, -60f), new Vector3(0, 0.5f, 0));
        Shot(cam, rt, outDir, "unity_04_lounge", new Vector3(-6f, 1.7f, -53f), new Vector3(-22f, 1.0f, -50f));
        Shot(cam, rt, outDir, "unity_05_bridge", new Vector3(0, 1.7f, -30f), new Vector3(0, 0.6f, 0));
        Shot(cam, rt, outDir, "unity_06_ring_dark", new Vector3(0, 9f, -14f), new Vector3(0, 0, 0));
        house.SetActive(true);
        Shot(cam, rt, outDir, "unity_07_desk", new Vector3(0, 1.75f, -0.35f), new Vector3(0, 0.85f, 1.2f));
        Shot(cam, rt, outDir, "unity_08_seats_house", new Vector3(3.5f, 1.6f, -3.0f), new Vector3(-6f, 0.5f, 4f));
        inner.SetActive(false); glow.SetActive(true);
        Shot(cam, rt, outDir, "unity_09_panels", new Vector3(0, 9f, -14f), new Vector3(0, 6f, 20f));
        Shot(cam, rt, outDir, "unity_10_desk_top", new Vector3(0, 2.4f, -1.5f), new Vector3(0, 0.9f, 0.3f));
        // the load look (House preset: house lights on, dome panels glowing) and a recliner close up
        Shot(cam, rt, outDir, "unity_11_recliner", new Vector3(-2.9f, 1.25f, 1.55f), new Vector3(-4.68f, 0.5f, 2.7f));
        Shot(cam, rt, outDir, "unity_12_house_default", new Vector3(5.6f, 1.7f, 4.2f), new Vector3(-20f, 12f, -12f));
        // vista layout (when it's the live one): from the entry landing, from a row 3 seat, and the stage from the front row
        var mount = GameObject.Find("Vista_Dais_Mount");
        if (mount != null)
        {
            var m = mount.transform.position;   // the dais on the vista stage
            Shot(cam, rt, outDir, "unity_20_vista_entrance", m + new Vector3(0, 4.35f, -11.8f), m + new Vector3(0, 1f, 6f));
            Shot(cam, rt, outDir, "unity_21_vista_seated", m + new Vector3(2.2f, 2.3f, -6.7f), new Vector3(0, 12f, 50f));
            Shot(cam, rt, outDir, "unity_22_vista_stage", m + new Vector3(-3.5f, 2.0f, -5.0f), m + new Vector3(0, 0.8f, 0));
            inner.SetActive(true); glow.SetActive(false);
            Shot(cam, rt, outDir, "unity_23_vista_dark_overview", m + new Vector3(16f, 10f, -8f), m + new Vector3(0, 0, -4f));
        }
        Object.DestroyImmediate(go);
        // diagnostics: are the concourse renderers lightmapped?
        var floor = GameObject.Find("Band_Floor").GetComponent<MeshRenderer>();
        var lm = LightmapSettings.lightmaps;
        var info = $"lightmaps {lm.Length}; Band_Floor lightmapIndex {floor.lightmapIndex} scaleOffset {floor.lightmapScaleOffset}";
        if (lm.Length > 0 && lm[0].lightmapColor != null)
        {
            var src = lm[0].lightmapColor;
            var tmp = RenderTexture.GetTemporary(64, 64, 0, RenderTextureFormat.ARGBHalf, RenderTextureReadWrite.Linear);
            Graphics.Blit(src, tmp); RenderTexture.active = tmp;
            var t = new Texture2D(64, 64, TextureFormat.RGBAHalf, false); t.ReadPixels(new Rect(0, 0, 64, 64), 0, 0); RenderTexture.active = null;
            float sum = 0, max = 0; foreach (var c in t.GetPixels()) { sum += c.maxColorComponent; max = Mathf.Max(max, c.maxColorComponent); }
            info += $"; lightmap mean {sum / 4096f:F3} max {max:F3} ({src.width}x{src.height})";
            RenderTexture.ReleaseTemporary(tmp);
        }
        File.WriteAllText(Path.Combine(outDir, "unity_diagnostics.txt"), info);
        Debug.Log("[Sphererebro] review shots written to " + outDir);
    }

    static void Shot(Camera cam, RenderTexture rt, string dir, string name, Vector3 eye, Vector3 target)
    {
        cam.transform.position = eye;
        cam.transform.rotation = Quaternion.LookRotation(target - eye, Vector3.up);
        cam.Render();
        RenderTexture.active = rt;
        var tex = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
        tex.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0); tex.Apply();
        RenderTexture.active = null;
        File.WriteAllBytes(Path.Combine(dir, name + ".png"), tex.EncodeToPNG());
        Object.DestroyImmediate(tex);
    }
}
