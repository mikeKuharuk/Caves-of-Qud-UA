using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The rules lines the game's C# writes into a description in English, under the item or creature
    /// («Keen: +2 to penetration rolls», «Requires training in Tinkering to use.»). Every one passes
    /// Extensions.AppendRules, which wraps it in {{rules|…}}; the text goes through the Rules code table first
    /// (codescan.scan_rules). What the string tables gave passes; a text an Action builds is out of reach.
    /// </summary>
    [HarmonyPatch]
    static class RulesPatch
    {
        // the overloads that take the text itself (StringBuilder and TextBuilder, with or without a procedure; some
        // are [Obsolete], hence the name as a string)
        static IEnumerable<MethodBase> TargetMethods() =>
            typeof(XRL.Extensions).GetMethods(BindingFlags.Public | BindingFlags.Static)
                .Where(m => m.Name == "AppendRules"
                            && m.GetParameters().Any(p => p.Name == "Text" && p.ParameterType == typeof(string)));

        static void Prefix(ref string Text)
        {
            if (!Uk.Active) return;
            Text = CodeText.Translate("Rules", Text);
        }
    }
}
