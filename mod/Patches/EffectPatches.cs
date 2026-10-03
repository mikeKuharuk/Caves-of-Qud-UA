using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using XRL.World;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// Effect names and descriptions the game's C# writes (DisplayName = "{{G|poisoned}}", GetDetails overrides): the
    /// HUD effect list, the character sheet, look descriptions. Every Effect class's own GetDescription,
    /// GetStateDescription and GetDetails is patched, and the text they return goes through the Effects code table,
    /// agreed with the effect's owner («отруєна» on a woman, «отруєні» on «ви»). Text the game already took from
    /// its string tables is Ukrainian and passes unchanged.
    /// </summary>
    [HarmonyPatch]
    static class EffectTextPatch
    {
        static readonly string[] Methods = { "GetDescription", "GetStateDescription", "GetDetails" };

        static IEnumerable<MethodBase> TargetMethods()
        {
            Type effect = typeof(Effect);
            foreach (Type type in effect.Assembly.GetTypes())
            {
                if (!effect.IsAssignableFrom(type) || type.ContainsGenericParameters) continue;  // open generics cannot be patched
                foreach (string name in Methods)
                {
                    MethodInfo method = AccessTools.DeclaredMethod(type, name, Type.EmptyTypes);
                    if (method != null && !method.IsAbstract && method.ReturnType == typeof(string)) yield return method;
                }
            }
        }

        static void Postfix(Effect __instance, ref string __result)
        {
            if (string.IsNullOrEmpty(__result) || !Uk.Active) return;
            __result = CodeText.Translate("Effects", __result, __instance.Object);
        }
    }
}
