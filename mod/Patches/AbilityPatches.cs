using HarmonyLib;
using XRL.World;
using XRL.World.Parts;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The names and descriptions the game's C# gives activated abilities in English (AddMyActivatedAbility("Intimidate",
    /// …), «Clone [3 left]» on a rename), from the Abilities code table. The entry keeps what it is given, and the
    /// ability bar, the ability list, the keybinding popups and the «can't be used» messages all read it there, so the
    /// name is translated where it goes in: when the ability is added, renamed, or read from a save made in English. A
    /// name the string tables already gave (_S, _T) is Ukrainian and passes. The parts keep the English they compare
    /// (Wings checks the jump's «Jump» on the event, before the name reaches the entry).
    /// </summary>
    [HarmonyPatch(typeof(ActivatedAbilities), nameof(ActivatedAbilities.AddAbility))]
    static class AbilityAddPatch
    {
        static void Prefix(ref string Name, ref string Description)
        {
            if (!Uk.Active) return;
            Name = CodeText.Translate("Abilities", Name);
            Description = CodeText.Translate("Abilities", Description);
        }
    }

    /// <summary>A name the code changes as it goes: «Tinker Turret  [2 remaining]», «Clone [1 left]».</summary>
    [HarmonyPatch(typeof(GameObject), nameof(GameObject.SetActivatedAbilityDisplayName))]
    static class AbilityRenamePatch
    {
        static void Prefix(ref string DisplayName)
        {
            if (!Uk.Active) return;
            DisplayName = CodeText.Translate("Abilities", DisplayName);
        }
    }

    /// <summary>An ability from a save made in English, or before the table knew its name.</summary>
    [HarmonyPatch(typeof(ActivatedAbilityEntry), nameof(ActivatedAbilityEntry.Read))]
    static class AbilityLoadPatch
    {
        static void Postfix(ActivatedAbilityEntry __instance)
        {
            if (!Uk.Active) return;
            __instance.DisplayName = CodeText.Translate("Abilities", __instance.DisplayName);
            __instance.Description = CodeText.Translate("Abilities", __instance.Description);
        }
    }
}
