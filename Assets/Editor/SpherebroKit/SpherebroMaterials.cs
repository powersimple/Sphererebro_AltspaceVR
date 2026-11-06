using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// The world's materials, made (or updated in place) by SpherebroBuilder. Names match the Blender material names, so the
// FBX importer remaps to them. Few textures, reused everywhere (borrowed from the Polys theatre): quality comes from these
// maps, not from polygons. Quest import limits live in each texture's .meta (max 2048, ASTC).
public static class SpherebroMaterials
{
    const string Dir = "Assets/_Spherebro/Materials";
    const string Tex = "Assets/_Spherebro/Textures/";

    static Texture2D T(string file) => AssetDatabase.LoadAssetAtPath<Texture2D>(Tex + file);

    class Spec
    {
        public Color color = Color.white; public float metal, smooth = 0.5f;
        public string albedo, normal, metalMap; public float normalScale = 1f; public Vector2 tiling = Vector2.one;
        public Color emission = Color.black; public bool transparent, unlit;
    }

    static readonly Dictionary<string, Spec> Specs = new Dictionary<string, Spec>
    {
        ["SB_SolarPanel"] = new Spec { albedo = "SolarPanel_Albedo.png", normal = "SolarPanel_Nrm.png", metalMap = "SolarPanel_metallic.png", metal = 1f, smooth = 0.75f, tiling = new Vector2(64, 32) },
        ["SB_SolarPanel_Glow"] = new Spec { albedo = "SolarPanel_Albedo.png", normal = "SolarPanel_Nrm.png", metal = 0.6f, smooth = 0.75f, tiling = new Vector2(64, 32), emission = new Color(0.32f, 0.36f, 0.48f) },
        ["SB_SphereScreen"] = new Spec { unlit = true, color = Color.white },
        ["SB_SphereOuter"] = new Spec { albedo = "CleanBronze_Albedo.png", normal = "CleanBronze_Nrm.png", color = new Color(0.45f, 0.36f, 0.3f), metal = 0.85f, smooth = 0.55f, tiling = new Vector2(24, 12) },
        ["SB_Bronze"] = new Spec { albedo = "CleanBronze_Albedo.png", normal = "CleanBronze_Nrm.png", metal = 1f, smooth = 0.72f },
        ["SB_Gold_EMIT"] = new Spec { color = new Color(1f, 0.72f, 0.3f), metal = 0.3f, smooth = 0.6f, emission = new Color(0.85f, 0.5f, 0.18f) },
        ["SB_Blue_EMIT"] = new Spec { color = new Color(0.2f, 0.55f, 1f), smooth = 0.6f, emission = new Color(0.3f, 0.9f, 2.0f) },
        ["SB_Signage_EMIT"] = new Spec { color = new Color(1f, 0.92f, 0.8f), emission = new Color(1.6f, 1.35f, 1.0f) },
        ["SB_Glass"] = new Spec { color = new Color(0.5f, 0.62f, 0.7f, 0.07f), metal = 0f, smooth = 0.7f, transparent = true },
        ["SB_FloorStone"] = new Spec { albedo = "TileFloor_albedo.png", normal = "TileFloor_Nrm.png", color = new Color(0.42f, 0.4f, 0.42f), smooth = 0.82f, tiling = new Vector2(0.5f, 0.5f) },
        ["SB_Ceiling"] = new Spec { color = new Color(0.16f, 0.12f, 0.1f), smooth = 0.25f },
        ["SB_WoodWall"] = new Spec { albedo = "Wood_Aged_1K_albedo.jpg", normal = "Wood_Aged_1K_normal.jpg", color = new Color(0.62f, 0.45f, 0.36f), smooth = 0.55f, tiling = new Vector2(0.5f, 0.5f) },
        ["SB_Leather"] = new Spec { color = new Color(0.36f, 0.035f, 0.045f), smooth = 0.5f, normal = "Fabric_Rug_006_NRM.jpg", normalScale = 0.25f, tiling = new Vector2(4, 4) },
        ["SB_Carbon"] = new Spec { albedo = "Carbon_Albedo.png", normal = "Carbon_Normal.png", smooth = 0.62f, metal = 0.2f, tiling = new Vector2(3, 3) },
        ["SB_BrushedMetal"] = new Spec { color = new Color(0.62f, 0.62f, 0.64f), normal = "BrushedMetal_N.png", metal = 1f, smooth = 0.68f, tiling = new Vector2(2, 2) },
        ["SB_Deck"] = new Spec { albedo = "SolarFloor_albedo.png", normal = "SolarFloor_Nrm.png", color = new Color(0.5f, 0.5f, 0.55f), metal = 0.4f, smooth = 0.6f, tiling = new Vector2(0.5f, 0.5f) },
        ["SB_InlayGold"] = new Spec { albedo = "CleanBronze_Albedo.png", color = new Color(1f, 0.85f, 0.55f), metal = 1f, smooth = 0.8f, emission = new Color(0.12f, 0.08f, 0.03f) },
        ["SB_InlayDark"] = new Spec { color = new Color(0.03f, 0.03f, 0.04f), metal = 0.3f, smooth = 0.85f },
        ["SB_BlackGlass"] = new Spec { color = new Color(0.01f, 0.01f, 0.015f), metal = 0.2f, smooth = 0.9f },
        ["SB_Rug"] = new Spec { color = new Color(0.28f, 0.05f, 0.07f), normal = "Fabric_Rug_006_NRM.jpg", smooth = 0.15f, tiling = new Vector2(2, 2) },
        ["SB_BottleGreen"] = new Spec { color = new Color(0.05f, 0.22f, 0.08f), metal = 0.1f, smooth = 0.92f },
        ["SB_FluteGlass"] = new Spec { color = new Color(0.85f, 0.92f, 0.95f, 0.3f), smooth = 0.95f, transparent = true },
        ["SB_Champagne"] = new Spec { color = new Color(0.95f, 0.78f, 0.35f), smooth = 0.9f, emission = new Color(0.25f, 0.18f, 0.05f) },
        ["SB_ButtonCap"] = new Spec { color = new Color(0.85f, 0.75f, 0.55f), metal = 0.5f, smooth = 0.7f, emission = new Color(0.5f, 0.38f, 0.18f) },
        ["SB_Fabric"] = new Spec { color = new Color(0.12f, 0.1f, 0.14f), normal = "Fabric_Rug_006_NRM.jpg", smooth = 0.2f, tiling = new Vector2(3, 3) },
        ["SB_Plant"] = new Spec { color = new Color(0.08f, 0.22f, 0.09f), smooth = 0.35f },
        ["SB_Orb_01"] = new Spec { color = new Color(1f, 0.72f, 0.3f), smooth = 0.8f, emission = new Color(1.4f, 0.9f, 0.3f) },
        ["SB_Orb_02"] = new Spec { color = new Color(0.2f, 0.85f, 0.85f), smooth = 0.8f, emission = new Color(0.2f, 1.2f, 1.2f) },
        ["SB_Orb_03"] = new Spec { color = new Color(0.9f, 0.2f, 0.6f), smooth = 0.8f, emission = new Color(1.3f, 0.25f, 0.8f) },
        ["SB_Orb_04"] = new Spec { color = new Color(0.25f, 0.4f, 1f), smooth = 0.8f, emission = new Color(0.3f, 0.55f, 1.6f) },
        ["SB_Orb_05"] = new Spec { color = new Color(1f, 0.45f, 0.15f), smooth = 0.8f, emission = new Color(1.5f, 0.6f, 0.2f) },
        ["SB_Orb_06"] = new Spec { color = new Color(0.6f, 0.3f, 1f), smooth = 0.8f, emission = new Color(0.8f, 0.4f, 1.5f) },
    };

    public static Dictionary<string, Material> MakeAll()
    {
        var lit = Shader.Find("Universal Render Pipeline/Lit");
        var unlit = Shader.Find("Universal Render Pipeline/Unlit");
        var result = new Dictionary<string, Material>();
        foreach (var kv in Specs)
        {
            var path = $"{Dir}/{kv.Key}.mat";
            var s = kv.Value;
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(s.unlit ? unlit : lit); AssetDatabase.CreateAsset(m, path); }
            m.shader = s.unlit ? unlit : lit;
            m.SetColor("_BaseColor", s.color);
            var a = s.albedo != null ? T(s.albedo) : null;
            m.SetTexture("_BaseMap", a); m.SetTextureScale("_BaseMap", s.tiling);
            if (!s.unlit)
            {
                m.SetFloat("_Metallic", s.metal); m.SetFloat("_Smoothness", s.smooth);
                var n = s.normal != null ? T(s.normal) : null;
                m.SetTexture("_BumpMap", n); m.SetFloat("_BumpScale", s.normalScale);
                if (n != null) m.EnableKeyword("_NORMALMAP"); else m.DisableKeyword("_NORMALMAP");
                var mm = s.metalMap != null ? T(s.metalMap) : null;
                m.SetTexture("_MetallicGlossMap", mm);
                if (mm != null) m.EnableKeyword("_METALLICSPECGLOSSMAP"); else m.DisableKeyword("_METALLICSPECGLOSSMAP");
                if (s.emission.maxColorComponent > 0)
                {
                    m.EnableKeyword("_EMISSION"); m.SetColor("_EmissionColor", s.emission);
                    if (s.albedo != null && kv.Key.EndsWith("_Glow")) m.SetTexture("_EmissionMap", a);
                    m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
                }
                else { m.DisableKeyword("_EMISSION"); m.SetColor("_EmissionColor", Color.black); m.globalIlluminationFlags = MaterialGlobalIlluminationFlags.EmissiveIsBlack; }
            }
            SetTransparent(m, s.transparent);
            EditorUtility.SetDirty(m);
            result[kv.Key] = m;
        }
        // the video sphere is black until its video's first frame replaces the base map
        result["SB_SphereScreen"].SetTexture("_BaseMap", BlackTexture());
        result["SB_Skybox"] = AssetDatabase.LoadAssetAtPath<Material>("Assets/_Spherebro/Skybox/WebXR Awards Skybox.mat");
        AssetDatabase.SaveAssets();
        return result;
    }

    static Texture2D BlackTexture()
    {
        const string path = Tex + "Black4.png";
        if (!System.IO.File.Exists(path))
        {
            var t = new Texture2D(4, 4, TextureFormat.RGB24, false);
            t.SetPixels(new Color[16]); t.Apply();
            System.IO.File.WriteAllBytes(path, t.EncodeToPNG());
            AssetDatabase.ImportAsset(path);
        }
        return T("Black4.png");
    }

    static void SetTransparent(Material m, bool on)
    {
        m.SetFloat("_Surface", on ? 1 : 0);
        m.SetOverrideTag("RenderType", on ? "Transparent" : "Opaque");
        m.SetFloat("_SrcBlend", on ? (float)BlendMode.SrcAlpha : (float)BlendMode.One);
        m.SetFloat("_DstBlend", on ? (float)BlendMode.OneMinusSrcAlpha : (float)BlendMode.Zero);
        m.SetFloat("_SrcBlendAlpha", on ? (float)BlendMode.One : (float)BlendMode.One);
        m.SetFloat("_DstBlendAlpha", on ? (float)BlendMode.OneMinusSrcAlpha : (float)BlendMode.Zero);
        m.SetFloat("_ZWrite", on ? 0 : 1);
        if (on) m.EnableKeyword("_SURFACE_TYPE_TRANSPARENT"); else m.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
        m.renderQueue = on ? (int)RenderQueue.Transparent : -1;
        m.SetShaderPassEnabled("DepthOnly", !on);
        m.SetShaderPassEnabled("ShadowCaster", !on);
    }
}
