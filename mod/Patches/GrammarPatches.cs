using System.Collections.Generic;
using CavesOfQudUA.Grammar;
using HarmonyLib;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The static English helpers in XRL.Language.Grammar, which the provider cannot override and the game's C# calls
    /// directly (docs/research/localization-gaps.md §3.1). Given a Ukrainian word they gave «сокираs», «пащеклац's»,
    /// «a пащеклац», «б’єs», «Меч З Каменю І Вогню», «the крила, the роги». With Ukrainian on, a word with Cyrillic
    /// letters is left as Ukrainian needs it; English words keep the English rules, since the code still builds
    /// English sentences around them until those are patched too.
    /// </summary>
    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.Pluralize), new[] { typeof(string) })]
    static class PluralizePatch
    {
        static bool Prefix(string word, ref string __result)
        {
            if (!Uk.Ours(word)) return true;
            __result = word;
            return false;
        }
    }

    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.MakePossessive), new[] { typeof(string) })]
    static class MakePossessivePatch
    {
        static bool Prefix(string word, ref string __result)
        {
            if (!Uk.Ours(word)) return true;
            __result = word;
            return false;
        }
    }

    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.A), new[] { typeof(string), typeof(bool) })]
    static class APatch
    {
        static bool Prefix(string Word, bool Capitalize, ref string __result)
        {
            if (!Uk.Ours(Word) || Word[0] == '=') return true;
            __result = Capitalize ? UkrainianForms.Capitalize(Word) : Word;
            return false;
        }
    }

    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.IndefiniteArticle), new[] { typeof(string), typeof(bool) })]
    static class IndefiniteArticlePatch
    {
        static bool Prefix(string Word, ref string __result)
        {
            if (!Uk.Ours(Word)) return true;
            __result = "";
            return false;
        }
    }

    /// <summary>Ukrainian titles capitalise the first word only; proper names inside keep their own capitals.</summary>
    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.MakeTitleCase), new[] { typeof(string) })]
    static class MakeTitleCasePatch
    {
        static bool Prefix(string Phrase, ref string __result)
        {
            if (!Uk.Ours(Phrase)) return true;
            __result = UkrainianForms.Capitalize(Phrase);
            return false;
        }
    }

    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.MakeTitleCaseWithArticle), new[] { typeof(string) })]
    static class MakeTitleCaseWithArticlePatch
    {
        static bool Prefix(string phrase, ref string __result)
        {
            if (!Uk.Ours(phrase)) return true;
            __result = UkrainianForms.Capitalize(phrase);
            return false;
        }
    }

    /// <summary>«the крила, the роги» → «крила, роги».</summary>
    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.MakeTheList))]
    static class MakeTheListPatch
    {
        static bool Prefix(IReadOnlyList<string> Words, bool Capitalize, ref string __result)
        {
            if (!Uk.Active || Words == null || Words.Count == 0 || !Uk.HasCyrillic(string.Join(" ", Words))) return true;
            string separator = ", ";
            foreach (string word in Words)
                if (word.Contains(",")) separator = "; ";
            string list = string.Join(separator, Words);
            __result = Capitalize ? UkrainianForms.Capitalize(list) : list;
            return false;
        }
    }

    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.ThirdPerson), new[] { typeof(string), typeof(bool) })]
    static class ThirdPersonPatch
    {
        static bool Prefix(string word, bool PrependSpace, ref string __result)
        {
            if (!Uk.Ours(word)) return true;
            __result = PrependSpace ? " " + word : word;
            return false;
        }
    }

    [HarmonyPatch(typeof(XRL.Language.Grammar), nameof(XRL.Language.Grammar.PastTenseOf), new[] { typeof(string) })]
    static class PastTenseOfPatch
    {
        static bool Prefix(string verb, ref string __result)
        {
            if (!Uk.Ours(verb)) return true;
            __result = verb;
            return false;
        }
    }

    /// <summary>
    /// Extensions.Things, the counts the code writes into its sentences: «You are crippled for 5 turns!», «You must
    /// wait 3 rounds». The code tables translate the sentence around the count as a hole, so the count itself must come
    /// out Ukrainian: «Вас скалічено на 5 ходів!» (UkrainianThings).
    /// </summary>
    [HarmonyPatch]
    static class ThingsPatch
    {
        static IEnumerable<System.Reflection.MethodBase> TargetMethods()
        {
            foreach (System.Type number in new[] { typeof(int), typeof(float), typeof(double) })
                yield return AccessTools.Method(typeof(XRL.Extensions), "Things",   // [Obsolete]: no nameof, no warning
                                                new[] { number, typeof(string), typeof(string) });
        }

        static bool Prefix(object[] __args, string what, ref string __result)
        {
            if (!Uk.Active || __args[0] == null) return true;
            string count = UkrainianThings.Count(System.Convert.ToDouble(__args[0]), __args[0].ToString(), what);
            if (count == null) return true;
            __result = count;
            return false;
        }
    }
}
