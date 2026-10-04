using CavesOfQudUA.Grammar;
using HarmonyLib;
using XRL.World.Anatomy;
using XRL.World.Capabilities;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// Body parts. Their names come from Bodies.uk.xml (tools/qudtr/datatables.py, bodies_xml); the game then puts the
    /// sides before them in English (Laterality.WithLateralityAdjective: «left arm») and an English ordinal before a
    /// name that repeats («second head», BodyPart.GetOrdinalName). For a Ukrainian name both come out Ukrainian and
    /// agreed with the noun (UkrainianLaterality): «ліва рука», «друга голова». The noun's gender is its qud-gender
    /// note (NounGenders, by the last words of the name).
    /// </summary>
    [HarmonyPatch(typeof(Laterality), nameof(Laterality.WithLateralityAdjective),
                  new[] { typeof(string), typeof(int), typeof(bool), typeof(bool) },
                  new[] { ArgumentType.Normal, ArgumentType.Normal, ArgumentType.Out, ArgumentType.Normal })]
    static class WithLateralityPatch
    {
        static bool Prefix(string Base, int Laterality, out bool Conjoin, bool Capitalized, ref string __result)
        {
            Conjoin = false;
            if (!Uk.Ours(Base)) return true;
            __result = UkrainianLaterality.With(Base, Laterality, BodyParts.GenderOf(Base), Capitalized);
            return false;
        }
    }

    /// <summary>The same words taken off again, before a part changes sides (BodyPart.ChangeLaterality).</summary>
    [HarmonyPatch(typeof(Laterality), nameof(Laterality.StripLateralityAdjective))]
    static class StripLateralityPatch
    {
        static bool Prefix(string Text, int Laterality, bool Capitalized, ref string __result)
        {
            if (!Uk.Ours(Text)) return true;
            __result = UkrainianLaterality.Strip(Text, Laterality, Capitalized);
            return false;
        }
    }

    [HarmonyPatch(typeof(BodyPart), nameof(BodyPart.GetOrdinalName))]
    static class OrdinalNamePatch
    {
        static bool Prefix(BodyPart __instance, ref string __result)
        {
            BodyPart part = __instance;
            if (!Uk.Ours(part.Name) || part.IgnorePosition || part.GetPartNameCount(part.Name) == 1) return true;
            __result = BodyParts.Colored(part, UkrainianLaterality.WithOrdinal(part.GetNamePosition(), part.Name,
                                                                                BodyParts.GenderOf(part.Name), false));
            return false;
        }
    }

    /// <summary>The equipment screen's «Друга ліва рука».</summary>
    [HarmonyPatch(typeof(BodyPart), nameof(BodyPart.GetOrdinalDescription))]
    static class OrdinalDescriptionPatch
    {
        static bool Prefix(BodyPart __instance, ref string __result)
        {
            BodyPart part = __instance;
            if (!Uk.Ours(part.Description) || part.IgnorePosition || part.GetPartDescriptionCount(part.Description) == 1)
                return true;
            string description = string.IsNullOrEmpty(part.DescriptionPrefix)
                ? part.Description
                : part.DescriptionPrefix + " " + part.Description;
            __result = BodyParts.Colored(part, UkrainianLaterality.WithOrdinal(part.GetDescriptionPosition(), description,
                                                                                BodyParts.GenderOf(part.Description), true));
            return false;
        }
    }

    static class BodyParts
    {
        /// <summary>The gender of a body part's name, by its last words («ліва рука» → «рука»).</summary>
        public static UkGender GenderOf(string name)
        {
            return UkrainianGender.OfZoneName(name) ?? UkGender.Masculine;
        }

        /// <summary>The name in its category's colour, as GetOrdinalName writes it.</summary>
        public static string Colored(BodyPart part, string text)
        {
            string color = part.Abstract ? null : BodyPartCategory.GetColor(part.Category);
            return color == null ? text : "{{" + color + "|" + text + "}}";
        }
    }
}
