using HarmonyLib;
using XRL;
using XRL.UI;
using XRL.World.Skills;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The skills list's line for a power the player has not learnt: «:Притискний вогонь [200 ОН] 25 Спритність, Draw
    /// a Bead». The game names a power it requires by the entry's Name, the English one (SPNode.ModernUIText), where
    /// an exclusion right below gets GetDisplayName. Each required entry's Name in the line becomes its display name.
    /// </summary>
    [HarmonyPatch(typeof(SPNode), nameof(SPNode.ModernUIText))]
    static class SkillRequirementNamesPatch
    {
        static void Postfix(SPNode __instance, ref string __result)
        {
            if (!Uk.Active || string.IsNullOrEmpty(__result) || string.IsNullOrEmpty(__instance.Power?.Requires)) return;
            foreach (string required in __instance.Power.Requires.CachedCommaExpansion())
            {
                if (!SkillFactory.Factory.TryGetFirstEntry(required, out IBaseSkillEntry entry)) continue;
                string english = entry.Name, shown = entry.GetDisplayName();
                if (english == null || english.Length < 3 || string.IsNullOrEmpty(shown) || shown == english) continue;
                __result = __result.Replace(english, shown);
            }
        }
    }
}
