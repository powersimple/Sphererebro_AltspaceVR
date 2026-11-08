// Stereo video for the talk's screens (side-by-side or top-bottom). Each eye samples its own half of the frame; on a flat
// display (no stereo) it shows the LEFT eye. URP, unlit, single-pass instanced safe. _Layout: 0 mono, 1 SBS (left|right),
// 2 TB (left on top). The video player writes the frame into _BaseMap (VideoPlayer Material Override).
Shader "SB/StereoVideo"
{
    Properties
    {
        _BaseMap ("Video", 2D) = "black" {}
        _BaseColor ("Tint", Color) = (1,1,1,1)
        [Enum(Mono,0,SideBySide,1,TopBottom,2)] _Layout ("Layout", Float) = 1
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Cull Off
        Pass
        {
            Name "Unlit"
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
            CBUFFER_START(UnityPerMaterial)
                float4 _BaseMap_ST;
                half4 _BaseColor;
                float _Layout;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; UNITY_VERTEX_OUTPUT_STEREO };

            Varyings vert(Attributes v)
            {
                Varyings o = (Varyings)0;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.uv = v.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
                float eye = 0;
                #if defined(UNITY_STEREO_INSTANCING_ENABLED) || defined(UNITY_STEREO_MULTIVIEW_ENABLED) || defined(UNITY_SINGLE_PASS_STEREO)
                    eye = unity_StereoEyeIndex;
                #endif
                float2 uv = i.uv;
                if (_Layout > 0.5 && _Layout < 1.5) uv.x = uv.x * 0.5 + eye * 0.5;
                else if (_Layout > 1.5) uv.y = uv.y * 0.5 + (1 - eye) * 0.5;
                return SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv) * _BaseColor;
            }
            ENDHLSL
        }
    }
}
