using System;
using System.Collections.Generic;
using System.Globalization;
using System.Reflection;
using XRL.Language;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// The language provider for Ukrainian. It keeps the English behaviour of TranslatorBase except where Ukrainian
    /// differs: no articles, lists without the serial comma, adjectives agreed in names and zone names, Ukrainian
    /// numerals and culture. Cases come in later steps of docs/grammar.md.
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
            ExtendCulling();
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

        // Around a variable that comes out empty the game removes one space, but only between characters it knows
        // as boundaries (GameText.ProcessCulling): ASCII quotes and brackets. Ukrainian typography adds guillemets,
        // the low-high quotes and the ellipsis, so «=x= сокира» left «« сокира»» with an empty x.
        static void ExtendCulling()
        {
            AddTo("LeftEaters", '«', '„', '“');
            AddTo("RightEaters", '»', '“', '”', '…');
        }

        static void AddTo(string field, params char[] chars)
        {
            FieldInfo info = typeof(XRL.GameText).GetField(field, BindingFlags.NonPublic | BindingFlags.Static);
            if (info?.GetValue(null) is HashSet<char> set)
                foreach (char c in chars) set.Add(c);
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

        /// <summary>No «a»/«the» before zone names either (recoilers, landing pads, the slynth sanctuary).</summary>
        public override void AddArticle(AddArticleParams Params)
        {
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

        /// <summary>
        /// A biome's adjective before a zone name agrees with the name: «слизька соляна пустеля», «іржаві руїни».
        /// The game inserts it as it is (TranslatorBase.MutateZoneName), and the adjectives are translated in the
        /// masculine.
        /// </summary>
        public override void MutateZoneName(MutateZoneNameParams Params)
        {
            if (!string.IsNullOrEmpty(Params.Adjective) && Params.Buffer.Length > 0)
            {
                UkGender? gender = UkrainianGender.OfZoneName(Params.Buffer.ToString());
                if (gender.HasValue)
                    Params.Adjective = UkrainianForms.AgreeAdjective(Params.Adjective, gender.Value, AdjectiveForms.Get, regular: true);
            }
            base.MutateZoneName(Params);
        }

        // ---- numbers: the English ones would print «12th», «second», «once» inside Ukrainian text ----

        public override string OrdinalWithDigits(long num)
        {
            return UkrainianNumbers.OrdinalDigits(num);
        }

        public override string Ordinal(long num)
        {
            return UkrainianNumbers.OrdinalWord(num);
        }

        public override string Cardinal(long num)
        {
            return num.ToString(CultureInfo.InvariantCulture);
        }

        public override string CardinalNo(long num)
        {
            return num.ToString(CultureInfo.InvariantCulture);
        }

        public override string Multiplicative(long num)
        {
            return UkrainianNumbers.Multiplicative(num);
        }

        // ---- culture: real-world dates in Ukrainian, Ukrainian collation ----
        // TranslatorBase keeps its culture and comparers in static fields shared with every provider, so ours are
        // our own. The game parses numbers with the invariant culture, so this changes only case mapping, two sorts
        // and the four real-world date replacers (CalendarReplacers).

        static CultureInfo culture;
        static StringComparer comparer, comparerIgnoreCase;

        public override CultureInfo GetCultureInfo()
        {
            if (culture == null)
            {
                try { culture = new CultureInfo("uk-UA"); }
                catch (CultureNotFoundException) { culture = CultureInfo.InvariantCulture; }
            }
            return culture;
        }

        public override StringComparer GetStringComparer()
        {
            return comparer ?? (comparer = StringComparer.Create(GetCultureInfo(), ignoreCase: false));
        }

        public override StringComparer GetStringComparerIgnoreCase()
        {
            return comparerIgnoreCase ?? (comparerIgnoreCase = StringComparer.Create(GetCultureInfo(), ignoreCase: true));
        }
    }
}
