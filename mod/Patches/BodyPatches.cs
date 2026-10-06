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

    /// <summary>The equipment screen's «Друга ліва рука», and «Спина» where the game writes «Worn on Back».</summary>
    [HarmonyPatch(typeof(BodyPart), nameof(BodyPart.GetOrdinalDescription))]
    static class OrdinalDescriptionPatch
    {
        static bool Prefix(BodyPart __instance, ref string __result)
        {
            BodyPart part = __instance;
            if (!Uk.Ours(part.Description)) return true;
            bool ordinal = !part.IgnorePosition && part.GetPartDescriptionCount(part.Description) != 1;
            if (!ordinal && !BodyParts.EnglishPrefix(part)) return true;
            string description = BodyParts.Described(part);
            __result = BodyParts.Colored(part, ordinal
                ? UkrainianLaterality.WithOrdinal(part.GetDescriptionPosition(), description, BodyParts.GenderOf(part.Description), true)
                : description);
            return false;
        }
    }

    /// <summary>
    /// A part's description with its position («Спина (2)»), the other form the equipment screen shows. The type's
    /// English DescriptionPrefix («Worn on» before the back and the hands, Bodies.xml; a save keeps it too) goes before a
    /// Ukrainian description: Ukrainian names the slot by the part alone, as it does the head and the feet.
    /// </summary>
    [HarmonyPatch(typeof(BodyPart), nameof(BodyPart.GetCardinalDescription))]
    static class CardinalDescriptionPatch
    {
        static bool Prefix(BodyPart __instance, ref string __result)
        {
            BodyPart part = __instance;
            if (!Uk.Ours(part.Description) || !BodyParts.EnglishPrefix(part)) return true;
            string text = part.Description;
            if (!part.IgnorePosition)
            {
                int position = part.GetDescriptionPosition();
                if (position != 1) text += " (" + position + ")";
            }
            __result = BodyParts.Colored(part, text);
            return false;
        }
    }

    /// <summary>
    /// A part from a save made before the names were Ukrainian keeps the English it got then: the equipment screen of
    /// such a character reads «Left Hand», «Worn on Back». A part whose name is still its type's, sides aside, takes the
    /// type's Ukrainian name and description, sided as ChangeLaterality sides them; a part the game or a mutation named
    /// otherwise stays as it is.
    /// </summary>
    [HarmonyPatch(typeof(BodyPart), nameof(BodyPart.ReadValues))]
    static class BodyPartLoadPatch
    {
        static void Postfix(BodyPart __instance)
        {
            BodyPart part = __instance;
            if (!Uk.Active || string.IsNullOrEmpty(part.Name) || Uk.HasCyrillic(part.Name)) return;
            try
            {
                BodyPartType type = part.GetVariantTypeModelIfExists();
                if (type == null || !Uk.HasCyrillic(type.Name)) return;
                string bare = Laterality.StripLateralityAdjective(part.Name, part.Laterality);
                if (!string.Equals(bare, part.VariantType ?? part.Type, System.StringComparison.OrdinalIgnoreCase)) return;
                part.Name = Laterality.WithLateralityAdjective(type.Name, part.Laterality);
                part.Description = Laterality.WithLateralityAdjective(type.Description, part.Laterality, Capitalized: true);
            }
            catch (System.Exception) { }   // a name left English must never break loading the save
        }
    }

    static class BodyParts
    {
        /// <summary>The gender of a body part's name, by its last words («ліва рука» → «рука»).</summary>
        public static UkGender GenderOf(string name)
        {
            return UkrainianGender.OfZoneName(name) ?? UkGender.Masculine;
        }

        /// <summary>Whether the part's type puts an English prefix before its description («Worn on»).</summary>
        public static bool EnglishPrefix(BodyPart part)
        {
            return !string.IsNullOrEmpty(part.DescriptionPrefix) && !Uk.HasCyrillic(part.DescriptionPrefix);
        }

        /// <summary>The description with the type's prefix, unless that prefix is English (EnglishPrefix).</summary>
        public static string Described(BodyPart part)
        {
            return string.IsNullOrEmpty(part.DescriptionPrefix) || EnglishPrefix(part)
                ? part.Description
                : part.DescriptionPrefix + " " + part.Description;
        }

        /// <summary>The name in its category's colour, as GetOrdinalName writes it.</summary>
        public static string Colored(BodyPart part, string text)
        {
            string color = part.Abstract ? null : BodyPartCategory.GetColor(part.Category);
            return color == null ? text : "{{" + color + "|" + text + "}}";
        }
    }
}
