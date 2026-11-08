using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// The world's materials, made (or updated in place) by SphererebroBuilder. Names match the Blender material names, so the
// FBX importer remaps to them. Few textures, reused everywhere (borrowed from the Polys theatre): quality comes from these
// maps, not from polygons. Quest import limits live in each texture's .meta (max 2048, ASTC).
public static class SphererebroMaterials
{
    const string Dir = "Assets/_Sphererebro/Materials";
    const string Tex = "Assets/_Sphererebro/Textures/";

    static Texture2D T(string file) => AssetDatabase.LoadAssetAtPath<Texture2D>(Tex + file);

    class Spec
    {
        public Color color = Color.white; public float metal, smooth = 0.5f;
        public string albedo, normal, metalMap; public float normalScale = 1f; public Vector2 tiling = Vector2.one;
        public Color emission = Color.black; public bool transparent, unlit, emissionFromAlbedo;
    }

    static readonly Dictionary<string, Spec> Specs = new Dictionary<string, Spec>
    {
        ["SB_SolarPanel"] = new Spec { albedo = "SolarPanel_Albedo.png", normal = "SolarPanel_Nrm.png", metalMap = "SolarPanel_metallic.png", metal = 1f, smooth = 0.75f, tiling = new Vector2(64, 32) },
        // the dome's default look (PANELS): dark purple with slightly lighter grey latitude and longitude lines every 15 deg
        // (Ben, 2026-11-07, "turn it down"). Matt, so the realtime house lights read on it; a faint self-glow from the same
        // texture keeps the grid visible when the house is low. The sphere's UVs are compass/latitude (the Blender script).
        ["SB_SolarPanel_Glow"] = new Spec { albedo = DomeGridFile, metal = 0f, smooth = 0.15f, emission = new Color(0.22f, 0.22f, 0.22f) },
        ["SB_SphereScreen"] = new Spec { unlit = true, color = Color.white },
        ["SB_SphereOuter"] = new Spec { albedo = "CleanBronze_Albedo.png", normal = "CleanBronze_Nrm.png", color = new Color(0.45f, 0.36f, 0.3f), metal = 0.85f, smooth = 0.55f, tiling = new Vector2(24, 12) },
        ["SB_Bronze"] = new Spec { albedo = "CleanBronze_Albedo.png", normal = "CleanBronze_Nrm.png", metal = 1f, smooth = 0.72f },
        ["SB_Gold_EMIT"] = new Spec { color = new Color(1f, 0.72f, 0.3f), metal = 0.3f, smooth = 0.6f, emission = new Color(0.85f, 0.5f, 0.18f) },
        ["SB_Blue_EMIT"] = new Spec { color = new Color(0.2f, 0.55f, 1f), smooth = 0.6f, emission = new Color(0.3f, 0.9f, 2.0f) },
        ["SB_Signage_EMIT"] = new Spec { color = new Color(1f, 0.92f, 0.8f), emission = new Color(1.6f, 1.35f, 1.0f) },
        ["SB_Glass"] = new Spec { color = new Color(0.5f, 0.62f, 0.7f, 0.07f), metal = 0f, smooth = 0.7f, transparent = true },
        // smooth 0.82 -> 0.55 (2026-11-07): the mirror-polished floor threw hot glints that shimmered in the headset
        ["SB_FloorStone"] = new Spec { albedo = "TileFloor_albedo.png", normal = "TileFloor_Nrm.png", color = new Color(0.58f, 0.55f, 0.56f), smooth = 0.55f, tiling = new Vector2(0.5f, 0.5f) },
        ["SB_Ceiling"] = new Spec { color = new Color(0.34f, 0.27f, 0.22f), smooth = 0.25f },
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
        // recliners: soft crushed velvet (low smoothness, strong fabric normal) with gold piping
        ["SB_Velvet"] = new Spec { color = new Color(0.46f, 0.05f, 0.075f), smooth = 0.3f, normal = "Fabric_Rug_006_NRM.jpg", normalScale = 0.7f, tiling = new Vector2(6, 6) },
        // metal 1 -> 0.35: inside the sphere there are no reflection probes, so fully metallic surfaces render black or hot
        ["SB_Piping"] = new Spec { albedo = "CleanBronze_Albedo.png", color = new Color(1f, 0.82f, 0.5f), metal = 0.35f, smooth = 0.5f },
        // rails (2026-11-07, "you can't see the banisters"): a glass that shows, and a satin bronze cap and posts that read
        // as bronze without reflection probes, with a faint warm glow so the rail edge is still there in Lights Out
        ["SB_RailGlass"] = new Spec { color = new Color(0.55f, 0.62f, 0.75f, 0.22f), smooth = 0.8f, transparent = true },
        ["SB_RailCap"] = new Spec { albedo = "CleanBronze_Albedo.png", color = new Color(0.85f, 0.65f, 0.42f), metal = 0.25f, smooth = 0.45f, emission = new Color(0.06f, 0.04f, 0.02f) },
        // concourse light fittings (2026-11-07, "too hot and flicker"): softer than the old signage-white pendants, and the
        // cove/sconce tints of the club zones (no green). Values ~0.5: they glow, they don't blow out.
        // pendants: the diffuser sits recessed inside the shade now, and glows softer still (Ben: "they still glare")
        ["SB_Pendant_EMIT"] = new Spec { color = new Color(1f, 0.88f, 0.7f), emission = new Color(0.3f, 0.23f, 0.15f) },
        // the desk (2026-11-07, Ben: "black matt, it has a hotspot"): no gloss, no metal
        // desk keys (2026-11-07): matt black pill with a thin gold chamfer; the legend (TextMeshPro) sits on the black face
        ["SB_KeyCap"] = new Spec { color = new Color(0.035f, 0.035f, 0.04f), metal = 0f, smooth = 0.25f },
        // the key face: the legend sheet (Blender renders it with ffmpeg) printed into the key; matt, no glow (Ben: glowing
        // keys with hotspots are banned)
        // 2026-11-07 (later), Ben: "make the buttons backlit, and persist even when you turn the lights off". The legend
        // sheet is also the emission map, so only the lettering glows (gold); the black key face doesn't, so no hotspot.
        ["SB_KeyFace"] = new Spec { albedo = "SB_KeyLegends.png", metal = 0f, smooth = 0.2f, emission = new Color(0.9f, 0.9f, 0.9f), emissionFromAlbedo = true },
        ["SB_KeyRim"] = new Spec { color = new Color(1f, 0.78f, 0.45f), metal = 0.3f, smooth = 0.5f, emission = new Color(0.35f, 0.24f, 0.1f) },
        // the video loading ring: cool white glow, readable in Lights Out
        ["SB_Load_EMIT"] = new Spec { color = new Color(0.75f, 0.9f, 1f), emission = new Color(0.9f, 1.2f, 1.6f) },
        // the desk is dim, not black, in Lights Out (Ben): a faint self-glow
        ["SB_DeskMatte"] = new Spec { color = new Color(0.03f, 0.03f, 0.035f), metal = 0f, smooth = 0.12f, emission = new Color(0.025f, 0.025f, 0.03f) },
        // the IPN cube (from Ben's IPN-Cube2.blend): smoked glass panels, glossy letters in the IPN red/green/blue that glow a
        // little (so the logo reads with the house lights down), white labels that glow
        ["SB_IPN_Panel"] = new Spec { color = new Color(0.7f, 0.72f, 0.78f, 0.28f), metal = 0.2f, smooth = 0.85f, transparent = true },
        ["SB_IPN_Red"] = new Spec { color = new Color(0.75f, 0.06f, 0.06f), metal = 0.1f, smooth = 0.75f, emission = new Color(0.35f, 0.02f, 0.02f) },
        ["SB_IPN_Green"] = new Spec { color = new Color(0.05f, 0.7f, 0.2f), metal = 0.1f, smooth = 0.75f, emission = new Color(0.02f, 0.32f, 0.08f) },
        ["SB_IPN_Blue"] = new Spec { color = new Color(0.06f, 0.3f, 0.85f), metal = 0.1f, smooth = 0.75f, emission = new Color(0.02f, 0.12f, 0.4f) },
        ["SB_IPN_Label"] = new Spec { color = Color.white, emission = new Color(0.9f, 0.9f, 0.9f) },
        ["SB_Cove_Amber"] = new Spec { color = new Color(1f, 0.62f, 0.3f), emission = new Color(0.6f, 0.34f, 0.12f) },
        ["SB_Cove_Blue"] = new Spec { color = new Color(0.25f, 0.45f, 1f), emission = new Color(0.12f, 0.24f, 0.65f) },
        ["SB_Cove_Violet"] = new Spec { color = new Color(0.62f, 0.25f, 1f), emission = new Color(0.36f, 0.12f, 0.62f) },
        ["SB_Cove_Rose"] = new Spec { color = new Color(1f, 0.3f, 0.55f), emission = new Color(0.6f, 0.15f, 0.3f) },
        ["SB_Sconce"] = new Spec { albedo = "CleanBronze_Albedo.png", color = new Color(0.35f, 0.27f, 0.2f), metal = 0.5f, smooth = 0.5f },
        ["SB_Wine"] = new Spec { color = new Color(0.95f, 0.8f, 0.4f), smooth = 0.9f, emission = new Color(0.25f, 0.18f, 0.05f) },
    };

    // ---- the key legend sheet (1024 x 512, made by the Blender generator): crisp small text up close, so mipmaps with
    // trilinear and anisotropic filtering, and ASTC 4x4 on Quest (the best ASTC; text blurs at 6x6). Clamped: no bleed.
    static void ConfigureLegends()
    {
        var path = Tex + "SB_KeyLegends.png";
        AssetDatabase.ImportAsset(path);
        var ti = (TextureImporter)AssetImporter.GetAtPath(path);
        if (ti == null) return;
        ti.mipmapEnabled = true; ti.filterMode = FilterMode.Trilinear; ti.anisoLevel = 8;
        ti.wrapMode = TextureWrapMode.Clamp; ti.maxTextureSize = 1024; ti.alphaSource = TextureImporterAlphaSource.None;
        var a = ti.GetPlatformTextureSettings("Android");
        a.overridden = true; a.maxTextureSize = 1024; a.format = TextureImporterFormat.ASTC_4x4; ti.SetPlatformTextureSettings(a);
        ti.SaveAndReimport();
    }

    // ---- the dome grid: made here (no source file), 2048 x 1024 equirect, a line every 15 deg ----------------------------
    const string DomeGridFile = "SB_DomeGrid.png";
    static readonly Color32 GridBack = new Color32(26, 17, 40, 255);    // dark purple
    static readonly Color32 GridLine = new Color32(96, 94, 104, 255);   // slightly lighter grey
    static void MakeDomeGrid()
    {
        var path = Tex + DomeGridFile;
        const int W = 2048, H = 1024; const float lineHalfPx = 1.6f;   // ~3 px wide at the equator (0.5 deg, ~45 cm at 50 m)
        var px = new Color32[W * H];
        float Cov(float d) => Mathf.Clamp01(lineHalfPx + 0.5f - d);   // 1 px of soft edge: no hard aliasing steps
        for (int y = 0; y < H; y++)
        {
            float v = (y + 0.5f) / H * 12f; float dy = Mathf.Abs(v - Mathf.Round(v)) * H / 12f;
            for (int x = 0; x < W; x++)
            {
                float u = (x + 0.5f) / W * 24f; float dx = Mathf.Abs(u - Mathf.Round(u)) * W / 24f;
                float c = Mathf.Max(Cov(dx), Cov(dy));
                px[y * W + x] = Color32.Lerp(GridBack, GridLine, c);
            }
        }
        var t = new Texture2D(W, H, TextureFormat.RGB24, false); t.SetPixels32(px); t.Apply();
        var png = t.EncodeToPNG(); Object.DestroyImmediate(t);
        if (!System.IO.File.Exists(path) || !System.Linq.Enumerable.SequenceEqual(System.IO.File.ReadAllBytes(path), png))
        {
            System.IO.File.WriteAllBytes(path, png);
            AssetDatabase.ImportAsset(path);
        }
        var ti = (TextureImporter)AssetImporter.GetAtPath(path);
        if (ti == null) return;
        bool dirty = false;
        void Set<T>(T cur, T want, System.Action<T> set) { if (!Equals(cur, want)) { set(want); dirty = true; } }
        Set(ti.mipmapEnabled, true, v => ti.mipmapEnabled = v);
        Set(ti.wrapModeU, TextureWrapMode.Repeat, v => ti.wrapModeU = v);
        Set(ti.wrapModeV, TextureWrapMode.Clamp, v => ti.wrapModeV = v);
        Set(ti.filterMode, FilterMode.Trilinear, v => ti.filterMode = v);
        Set(ti.anisoLevel, 8, v => ti.anisoLevel = v);
        Set(ti.maxTextureSize, 2048, v => ti.maxTextureSize = v);
        var android = ti.GetPlatformTextureSettings("Android");
        if (!android.overridden || android.maxTextureSize != 2048 || android.format != TextureImporterFormat.ASTC_6x6)
        { android.overridden = true; android.maxTextureSize = 2048; android.format = TextureImporterFormat.ASTC_6x6; ti.SetPlatformTextureSettings(android); dirty = true; }
        if (dirty) ti.SaveAndReimport();
    }

    // ---- the skybox (2026-11-07, "the skybox is crap"): Ben's 8K equirect, imported as a cubemap. A cube face of 2048 px
    // covers 90 deg, the same detail as an 8192 px wide equirect, so Quest keeps the full 8K fidelity inside its 2048 limit
    // (SDK performance doc). Optimised (Ben, 2026-11-07, "but optimize it"), six 2048 px faces:
    //   Quest ASTC 6x6, best quality: 3.56 bits a pixel, ~11 MB (ASTC 4x4 would be ~25 MB for detail a star field doesn't
    //   need; 2048 px over 90 deg is ~23 px a degree, about what Quest 3 resolves, so the faces stay full size).
    //   PC BC7: ~25 MB, PC has the memory, and DXT1 smears tiny stars into coloured blocks.
    //   No mipmaps (a third more memory for nothing: the sky is never seen small), RGB only, no read/write copy.
    // Source: Skybox/Sphererebro_Sky_8K.(jpg|png) (Ben's file, copied in unchanged). Missing: the old skybox stays.
    public const string SkyDir = "Assets/_Sphererebro/Skybox/";
    static Material MakeSkybox()
    {
        string src = new[] { "Sphererebro_Sky_8K.png", "Sphererebro_Sky_8K.jpg" }.Select(f => SkyDir + f).FirstOrDefault(System.IO.File.Exists);
        if (src == null) return null;
        var ti = (TextureImporter)AssetImporter.GetAtPath(src);
        if (ti == null) return null;
        bool dirty = false;
        if (ti.textureShape != TextureImporterShape.TextureCube) { ti.textureShape = TextureImporterShape.TextureCube; dirty = true; }
        if (ti.generateCubemap != TextureImporterGenerateCubemap.Cylindrical) { ti.generateCubemap = TextureImporterGenerateCubemap.Cylindrical; dirty = true; }
        if (ti.mipmapEnabled) { ti.mipmapEnabled = false; dirty = true; }
        if (ti.npotScale != TextureImporterNPOTScale.ToNearest) { ti.npotScale = TextureImporterNPOTScale.ToNearest; dirty = true; }
        if (ti.maxTextureSize != 2048) { ti.maxTextureSize = 2048; dirty = true; }
        if (ti.filterMode != FilterMode.Bilinear) { ti.filterMode = FilterMode.Bilinear; dirty = true; }
        if (ti.isReadable) { ti.isReadable = false; dirty = true; }
        if (ti.alphaSource != TextureImporterAlphaSource.None) { ti.alphaSource = TextureImporterAlphaSource.None; dirty = true; }
        if (ti.streamingMipmaps) { ti.streamingMipmaps = false; dirty = true; }
        foreach (var (plat, fmt) in new[] { ("Standalone", TextureImporterFormat.BC7), ("Android", TextureImporterFormat.ASTC_6x6) })
        {
            var p = ti.GetPlatformTextureSettings(plat);
            if (!p.overridden || p.maxTextureSize != 2048 || p.format != fmt || p.compressionQuality != 100)
            { p.overridden = true; p.maxTextureSize = 2048; p.format = fmt; p.compressionQuality = 100; ti.SetPlatformTextureSettings(p); dirty = true; }
        }
        if (dirty) ti.SaveAndReimport();
        var cube = AssetDatabase.LoadAssetAtPath<Cubemap>(src);
        if (cube == null) return null;
        const string matPath = "Assets/_Sphererebro/Skybox/SB_Skybox.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        var sh = Shader.Find("Skybox/Cubemap");
        if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, matPath); }
        m.shader = sh; m.SetTexture("_Tex", cube); m.SetFloat("_Exposure", 1f); m.SetFloat("_Rotation", 0f);
        m.SetColor("_Tint", new Color(0.5f, 0.5f, 0.5f, 1f));
        EditorUtility.SetDirty(m);
        SkyFaceSize = cube.width;
        return m;
    }
    public static int SkyFaceSize;

    public static Dictionary<string, Material> MakeAll()
    {
        MakeDomeGrid();
        ConfigureLegends();
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
                    if (s.albedo != null && (kv.Key.EndsWith("_Glow") || s.emissionFromAlbedo)) m.SetTexture("_EmissionMap", a);
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
        // the 8K skybox when its file is there, else the old one (unchanged)
        result["SB_Skybox"] = MakeSkybox() ?? AssetDatabase.LoadAssetAtPath<Material>("Assets/_Sphererebro/Skybox/WebXR Awards Skybox.mat");
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
