using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using XRL;
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

    /// <summary>
    /// Stuck's state, «stuck in a web»: the effect's name (DisplayName) in the effect list, the tag after a name
    /// («[stuck in …]») and «X are stuck in a web!» (DidX, whose key «X|are|||{0}|!» takes it into its hole). Stuck builds
    /// it in GetStateDescription(From), which takes a parameter, so EffectTextPatch does not see it. The three places
    /// need a form with no gender, as the effect names do («у польоті»): what holds you, in the locative, «у павутинні»;
    /// nothing, «у пастці». Grabber's adjective comes from the string tables already («схоплено — X») and stays.
    /// </summary>
    [HarmonyPatch(typeof(XRL.World.Effects.Stuck), nameof(XRL.World.Effects.Stuck.GetStateDescription),
                  new[] { typeof(GameObject) })]
    public static class StuckStatePatch
    {
        static void Postfix(XRL.World.Effects.Stuck __instance, GameObject From, ref string __result)
        {
            if (!Uk.Active || string.IsNullOrEmpty(__result)) return;
            string state = State(__instance, From);
            if (state != null) __result = state;
        }

        /// <summary>The holder Stuck's own methods find: the one given, else the DependsOn object; null if gone.</summary>
        public static GameObject Holder(XRL.World.Effects.Stuck stuck, GameObject from)
        {
            GameObject holder = from;
            if (holder == null && !string.IsNullOrEmpty(stuck.DependsOn)) holder = GameObject.FindByID(stuck.DependsOn);
            return GameObject.Validate(ref holder) ? holder : null;
        }

        /// <summary>The state in Ukrainian, or null to leave the game's (an adjective the string tables gave, or another
        /// preposition than «in», which the game never passes with «stuck»).</summary>
        public static string State(XRL.World.Effects.Stuck stuck, GameObject from)
        {
            if (stuck.Adjective != "stuck") return null;
            GameObject holder = Holder(stuck, from);
            if (holder == null) return "у пастці";
            if (stuck.Preposition != "in") return null;
            return "у =object.n:loc=".StartReplace().SetObject(holder).ToString();
        }
    }

    /// <summary>
    /// Stuck's details begin with a line of its own English: «Stuck in a web» or «Stuck where it is.» (the line under
    /// it, the saving-throw bonus, the string tables give). In Ukrainian, with no gender: «Тримає павутиння.»,
    /// «Не може зрушити з місця.». First among the postfixes, so EffectTextPatch finds the line Ukrainian already.
    /// </summary>
    [HarmonyPatch(typeof(XRL.World.Effects.Stuck), nameof(XRL.World.Effects.Stuck.GetDetails))]
    static class StuckDetailsPatch
    {
        [HarmonyPriority(Priority.First)]
        static void Postfix(XRL.World.Effects.Stuck __instance, ref string __result)
        {
            if (!Uk.Active || string.IsNullOrEmpty(__result) || __instance.Adjective != "stuck") return;
            int end = __result.IndexOf('\n');
            string first = end < 0 ? __result : __result.Substring(0, end);
            if (!first.StartsWith("Stuck ", StringComparison.Ordinal)) return;
            GameObject holder = StuckStatePatch.Holder(__instance, null);
            string line = holder == null ? "Не може зрушити з місця."
                                         : "Тримає =object.name=.".StartReplace().SetObject(holder).ToString();
            __result = end < 0 ? line : line + __result.Substring(end);
        }
    }
}
