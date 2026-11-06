using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

// House rule: no icons in the Scene view. Unity draws a picture over every object for many component types (Banter's
// green "BS", TextMeshPro's blue "T", lights, cameras, audio sources, scripts...), and in a world this dense they bury
// what they mark. Each new component type turns its icon back on, so this runs on every editor load and domain reload and
// switches every component icon off. Outline gizmos (a light's range, a collider's box, the SDK's mirror and portal
// frames) are not icons and are left alone. Delete this file to get the icons back.
static class SpherebroHideIcons
{
    [InitializeOnLoadMethod]
    static void Hook()
    {
        EditorApplication.delayCall += Apply;
    }

    static void Apply()
    {
        // Every component type by its short name (a gizmo entry names its type that way). Only types Unity has a gizmo
        // entry for are touched: SetIconEnabled on any other type logs "Annotation not found!".
        var byName = new Dictionary<string, List<Type>>();
        foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type[] types;
            try { types = assembly.GetTypes(); }
            catch (Exception) { continue; }
            foreach (var type in types)
            {
                if (type.IsAbstract || !typeof(Component).IsAssignableFrom(type)) continue;
                if (!byName.TryGetValue(type.Name, out var list)) byName[type.Name] = list = new List<Type>();
                list.Add(type);
            }
        }
        int hidden = 0;
        foreach (var info in GizmoUtility.GetGizmoInfo())
        {
            if (!info.hasIcon || !info.iconEnabled || info.name == null) continue;
            var scripted = info.script is MonoScript ms ? ms.GetClass() : null;
            var types = scripted != null ? new List<Type> { scripted } : byName.TryGetValue(info.name, out var l) ? l : null;
            if (types == null) continue;
            foreach (var type in types) GizmoUtility.SetIconEnabled(type, false);
            hidden++;
        }
        if (hidden > 0)
            Debug.Log("[SpherebroHideIcons] Scene view icons off for " + hidden + " more type(s).");
    }
}
