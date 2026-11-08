using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

// A small JSON reader for the talk builder (JsonUtility can't read free-form objects). Objects -> Dictionary<string, object>,
// arrays -> List<object>, numbers -> double, true/false -> bool, null -> null.
public static class SphererebroTalkJson
{
    public static object Parse(string s) { int i = 0; var v = Val(s, ref i); return v; }

    static void Ws(string s, ref int i) { while (i < s.Length && (char.IsWhiteSpace(s[i]) || s[i] == '﻿')) i++; }

    static object Val(string s, ref int i)
    {
        Ws(s, ref i);
        char c = s[i];
        if (c == '{')
        {
            var d = new Dictionary<string, object>(); i++;
            Ws(s, ref i); if (s[i] == '}') { i++; return d; }
            while (true)
            {
                Ws(s, ref i); var k = Str(s, ref i); Ws(s, ref i); i++; // ':'
                d[k] = Val(s, ref i); Ws(s, ref i);
                if (s[i] == ',') { i++; continue; }
                i++; return d;
            }
        }
        if (c == '[')
        {
            var l = new List<object>(); i++;
            Ws(s, ref i); if (s[i] == ']') { i++; return l; }
            while (true)
            {
                l.Add(Val(s, ref i)); Ws(s, ref i);
                if (s[i] == ',') { i++; continue; }
                i++; return l;
            }
        }
        if (c == '"') return Str(s, ref i);
        if (s.Substring(i).StartsWith("true")) { i += 4; return true; }
        if (s.Substring(i).StartsWith("false")) { i += 5; return false; }
        if (s.Substring(i).StartsWith("null")) { i += 4; return null; }
        int j = i;
        while (j < s.Length && "+-0123456789.eE".IndexOf(s[j]) >= 0) j++;
        var num = double.Parse(s.Substring(i, j - i), CultureInfo.InvariantCulture); i = j; return num;
    }

    static string Str(string s, ref int i)
    {
        var sb = new StringBuilder(); i++;
        while (s[i] != '"')
        {
            if (s[i] == '\\')
            {
                i++; char e = s[i];
                if (e == 'n') sb.Append('\n'); else if (e == 't') sb.Append('\t'); else if (e == 'r') sb.Append('\r');
                else if (e == 'u') { sb.Append((char)Convert.ToInt32(s.Substring(i + 1, 4), 16)); i += 4; }
                else sb.Append(e);
                i++;
            }
            else sb.Append(s[i++]);
        }
        i++; return sb.ToString();
    }

    // helpers
    public static Dictionary<string, object> O(object o) => o as Dictionary<string, object>;
    public static List<object> L(object o) => o as List<object>;
    public static float F(object o, float def = 0f) => o == null ? def : o is double d ? (float)d : o is bool b ? (b ? 1 : 0) : def;
    public static string S(object o, string def = null) => o as string ?? def;
    public static object G(Dictionary<string, object> d, string k) => d != null && d.TryGetValue(k, out var v) ? v : null;
    public static float[] Fa(object o) { var l = L(o); if (l == null) return null; var a = new float[l.Count]; for (int i = 0; i < l.Count; i++) a[i] = F(l[i]); return a; }

    public static string Write(object o)
    {
        var sb = new StringBuilder(); W(sb, o); return sb.ToString();
    }
    static void W(StringBuilder sb, object o)
    {
        switch (o)
        {
            case null: sb.Append("null"); break;
            case string s:
                sb.Append('"');
                foreach (var ch in s)
                {
                    if (ch == '"' || ch == '\\') sb.Append('\\').Append(ch);
                    else if (ch == '\n') sb.Append("\\n");
                    else if (ch < 32 || ch > 126) sb.Append("\\u").Append(((int)ch).ToString("x4"));
                    else sb.Append(ch);
                }
                sb.Append('"'); break;
            case bool b: sb.Append(b ? "true" : "false"); break;
            case double d: sb.Append(d.ToString("0.####", CultureInfo.InvariantCulture)); break;
            case float f: sb.Append(f.ToString("0.####", CultureInfo.InvariantCulture)); break;
            case int n: sb.Append(n); break;
            case IDictionary<string, object> dict:
                sb.Append('{'); bool first = true;
                foreach (var kv in dict) { if (!first) sb.Append(','); first = false; W(sb, kv.Key); sb.Append(':'); W(sb, kv.Value); }
                sb.Append('}'); break;
            case System.Collections.IEnumerable list:
                sb.Append('['); bool f1 = true;
                foreach (var x in list) { if (!f1) sb.Append(','); f1 = false; W(sb, x); }
                sb.Append(']'); break;
            default: sb.Append(Convert.ToString(o, CultureInfo.InvariantCulture)); break;
        }
    }
}
