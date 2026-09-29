using System.Collections.Generic;
using System.Reflection;
using XRL.Language;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// The language provider for Ukrainian. It keeps the English behaviour of TranslatorBase except where Ukrainian
    /// differs; the rest (cases, adjective agreement, numbers in words, culture) comes in later steps of
    /// docs/grammar.md and needs a check in the game first.
    /// </summary>
    [LanguageProvider("uk")]
    public class UkrainianProvider : TranslatorBase
    {
        // The name generator rerolls a name that contains one of these (Grammar.ContainsBadWords); the game knows
        // only English ones. Ukrainian syllables glue into obscene words now and then («Хую…», «Сука…»), so the
        // provider, which exists only while the game runs in Ukrainian, adds the roots.
        static readonly string[] BadRoots =
        {
            "хуй", "хуя", "хує", "хую", "пизд", "їба", "їбу", "їбе", "єба", "йоб", "бля", "сука", "курв", "підор",
            "підар", "жоп", "гівн", "срак", "дроч", "мудак", "манда",
        };
        static readonly string[] BadWholeNames = { "кал", "сук", "їб" };

        public UkrainianProvider()
        {
            Extend("badWords", BadRoots);
            Extend("badWordsExact", BadWholeNames);
        }

        static void Extend(string field, string[] words)
        {
            FieldInfo info = typeof(XRL.Language.Grammar).GetField(field, BindingFlags.NonPublic | BindingFlags.Static);
            if (info == null || !(info.GetValue(null) is string[] current)) return;
            var merged = new List<string>(current);
            foreach (string word in words)
                if (!merged.Contains(word)) merged.Add(word);
            info.SetValue(null, merged.ToArray());
        }

        /// <summary>Names whose adjectives agree with the object's gender (UkrainianDescriptionBuilder).</summary>
        public override XRL.World.DescriptionBuilder CreateDescriptionBuilder(int Cutoff = int.MaxValue, bool BaseOnly = false)
        {
            // TranslatorBase ignores Cutoff here too
            return new UkrainianDescriptionBuilder(int.MaxValue, BaseOnly);
        }

        /// <summary>Ukrainian has no articles.</summary>
        public override string DefiniteArticle(DefiniteArticleParams Params)
        {
            return "";
        }

        public override string IndefiniteArticle(IndefiniteArticleParams Params)
        {
            return "";
        }

        /// <summary>«А, Б і В»: no comma before the conjunction (the separators themselves come from the string table).</summary>
        public override string MakeAndList(IReadOnlyList<string> List, MakeAndListParams Params = default)
        {
            return base.MakeAndList(List, new MakeAndListParams(false));
        }

        public override string MakeOrList(IReadOnlyList<string> List, MakeOrListParams Params = default)
        {
            return base.MakeOrList(List, new MakeOrListParams(false));
        }
    }
}
