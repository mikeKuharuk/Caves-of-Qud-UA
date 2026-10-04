using System;
using CavesOfQudUA.Grammar;
using HarmonyLib;
using Qud.UI;
using XRL.Language;
using XRL.UI;
using XRL.UI.Framework;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// Labels a Unity scene or prefab carries, which no code or table holds («SECONDARY ATTRIBUTES», «delete»): a
    /// text under root whose text is a Words key (codescan.PREFAB_WORDS) gets its Ukrainian, any markup around it
    /// staying. Only the game can run it, and none of these labels has been seen translated in the game yet: one that
    /// is no UITextSkin stays English.
    /// </summary>
    static class PrefabLabels
    {
        public static void Translate(UnityEngine.GameObject root)
        {
            if (root == null) return;
            try
            {
                foreach (UITextSkin skin in root.GetComponentsInChildren<UITextSkin>(true))
                {
                    string plain = UkrainianForms.StripMarkup(skin.text ?? "").Trim();
                    string word = plain.Length > 0 ? CodeTables.Get("Words", plain) : null;
                    if (word != null) skin.SetText(skin.text.Replace(plain, word));
                }
            }
            catch (Exception) { }   // a label left English must never break a screen
        }
    }

    /// <summary>The character screen's headers that only its scene has: «SECONDARY ATTRIBUTES», «RESISTANCES».</summary>
    [HarmonyPatch(typeof(CharacterStatusScreen), nameof(CharacterStatusScreen.UpdateViewFromData))]
    static class StatusHeadersPatch
    {
        static void Postfix(CharacterStatusScreen __instance)
        {
            if (Uk.Active) PrefabLabels.Translate(__instance.gameObject);
        }
    }

    /// <summary>
    /// A mutation's rank on the character screen: the game sets it from the string tables («{{G|РАНГ 3/10}}») and at
    /// once again in English («{{G|RANK 3/10}}», CharacterStatusScreen.HandleHighlightMutation). The string tables'
    /// line goes back in.
    /// </summary>
    [HarmonyPatch(typeof(CharacterStatusScreen), nameof(CharacterStatusScreen.HandleHighlightMutation))]
    static class MutationRankPatch
    {
        static void Postfix(CharacterStatusScreen __instance, FrameworkDataElement element)
        {
            if (!Uk.Active || !(element is CharacterMutationLineData line) || line.mutation == null) return;
            UITextSkin rank = __instance.mutationRankText;
            if (rank == null || string.IsNullOrEmpty(rank.text)) return;   // a mutation with no rank shows none
            try
            {
                Strings._T("CharacterStatusScreen MutationRankText", "{{G|RANK =level=/10}}")
                    .SetArgument("level", line.mutation.Level).SetUITextSkin(rank);
            }
            catch (Exception) { }
        }
    }

    /// <summary>The world creation screen's eons under their icons, which only its scene has («GEOLOGIC»).</summary>
    [HarmonyPatch(typeof(WorldGenerationScreen), nameof(WorldGenerationScreen.Show))]
    static class WorldGenerationLabelsPatch
    {
        static void Postfix(WorldGenerationScreen __instance)
        {
            if (Uk.Active) PrefabLabels.Translate(__instance.gameObject);
        }
    }
}
