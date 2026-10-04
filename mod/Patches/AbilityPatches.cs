using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.RegularExpressions;
using CavesOfQudUA.Grammar;
using HarmonyLib;
using XRL;
using XRL.World;
using XRL.World.Parts;
using XRL.World.Text.Delegates;

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

    /// <summary>
    /// The description the code builds again from the ability's template with its numbers (DescribeActivatedAbility,
    /// on each change of level, stance or equipment). The template is Ukrainian; the lines Templates.StatCollector adds
    /// under it are English («Cooldown reduced by 5 due to Сила волі: висока.», «Damage increased by 1-2 due to high
    /// strength.»): those go through the Abilities table line by line, the template's own lines pass.
    /// </summary>
    [HarmonyPatch]
    static class AbilityDescribePatch
    {
        static IEnumerable<MethodBase> TargetMethods()
        {
            return typeof(GameObject).GetMethods().Where(m => m.Name == nameof(GameObject.DescribeActivatedAbility));
        }

        static void Postfix(GameObject __instance, Guid ID)
        {
            if (!Uk.Active) return;
            ActivatedAbilityEntry entry = __instance.GetActivatedAbility(ID);
            if (entry != null) entry.Description = CodeText.Translate("Abilities", entry.Description);
        }
    }

    /// <summary>
    /// A statistic's value a description shows as the code set it, in English: «Дальність: sight», «Кидок проти
    /// падіння: Strength 21» (StatCollector.Set). While the value renders (XMLTemplateReplacers.Value: stat and statline
    /// nodes, never a switch), it is the Words table's Ukrainian, or a statistic's title before its number («Сила 21»);
    /// then the collector has its English back, for a switch that compares it.
    /// </summary>
    [HarmonyPatch(typeof(XMLTemplateReplacers), nameof(XMLTemplateReplacers.Value))]
    static class StatValuePatch
    {
        static void Prefix(Templates.StatCollector Stats, string Key, out string __state)
        {
            __state = null;
            if (!Uk.Active || Stats == null || Key == null
                || !Stats.values.TryGetValue(Key, out (string text, bool changes, int changedState) entry)) return;
            string shown = StatValues.Shown(entry.text);
            if (shown == null) return;
            __state = entry.text;
            Stats.values[Key] = (shown, entry.changes, entry.changedState);
        }

        static void Postfix(Templates.StatCollector Stats, string Key, string __state)
        {
            if (__state == null || !Stats.values.TryGetValue(Key, out (string text, bool changes, int changedState) entry))
                return;
            Stats.values[Key] = (__state, entry.changes, entry.changedState);
        }
    }

    public static class StatValues
    {
        static readonly Regex StatAndNumber = new Regex(@"^([A-Z][A-Za-z]+) (\d+)$");

        /// <summary>The Ukrainian a statistic's value shows, or null: no English in it, or no table knows it.</summary>
        public static string Shown(string value)
        {
            if (!CodeText.HasEnglish(value)) return null;
            string word = CodeTables.Get("Words", value);
            if (word != null) return word;
            Match m = StatAndNumber.Match(value);
            string title = m.Success ? CodeText.StatTitle(m.Groups[1].Value) : null;
            return title == null ? null : title + " " + m.Groups[2].Value;
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
