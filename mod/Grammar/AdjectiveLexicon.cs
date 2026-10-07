using System.Collections.Generic;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// Words of the translation, in lower case, for UkrainianCases to read a name by: the masculine adjectives it uses
    /// («слоновий», «синій»), the nouns that stand alone as a name («мавпа», «дочка»), and the stems of the nouns it
    /// declines («труб», «пісн», «тін» by «трубою», «піснею», «тінню»; «залишк» by «залишків»). `py tools/qud.py
    /// build` fills them into AdjectiveLexicon.g.cs (commands.adjective_lexicon, noun_lexicon, noun_stems); without
    /// that file they are empty. «слонова» is an adjective, «слоновий» being in here; «дочка» is a noun; «труби» is
    /// the plural of a feminine noun, so its genitive is «труб», and «залишки» of a masculine, so «залишків».
    /// </summary>
    public static partial class AdjectiveLexicon
    {
        static readonly HashSet<string> Words = new HashSet<string>();
        static readonly HashSet<string> NounWords = new HashSet<string>();
        static readonly HashSet<string> HardFeminine = new HashSet<string>();
        static readonly HashSet<string> SoftFeminine = new HashSet<string>();
        static readonly HashSet<string> ThirdDeclension = new HashSet<string>();
        static readonly HashSet<string> MasculinePlural = new HashSet<string>();

        static AdjectiveLexicon()
        {
            Fill(Words);
            FillNouns(NounWords);
            FillStems(HardFeminine, SoftFeminine, ThirdDeclension, MasculinePlural);
        }

        static partial void Fill(HashSet<string> t);

        static partial void FillNouns(HashSet<string> t);

        static partial void FillStems(HashSet<string> hard, HashSet<string> soft, HashSet<string> third, HashSet<string> masculine);

        public static bool Contains(string word) => word != null && Words.Contains(word);

        public static bool IsNoun(string word) => word != null && NounWords.Contains(word);

        /// <summary>A stem the translation declines as a hard feminine noun (труб: «трубою»).</summary>
        public static bool IsFeminineStem(string stem) => stem != null && HardFeminine.Contains(stem);

        /// <summary>A stem the translation declines as a soft feminine noun (пісн: «піснею»).</summary>
        public static bool IsSoftFeminineStem(string stem) => stem != null && SoftFeminine.Contains(stem);

        /// <summary>The stem of a feminine noun on a consonant (тін: «тінню»; кист: «кистю»).</summary>
        public static bool IsThirdDeclensionStem(string stem) => stem != null && ThirdDeclension.Contains(stem);

        /// <summary>The stem of a plural the translation puts in the genitive on -ів (залишк: «залишків»).</summary>
        public static bool IsMasculinePluralStem(string stem) => stem != null && MasculinePlural.Contains(stem);

        /// <summary>For tools/grammar-tests: a word added by hand.</summary>
        public static void Add(string word) => Words.Add(word);

        /// <summary>For tools/grammar-tests: a noun added by hand.</summary>
        public static void AddNoun(string word) => NounWords.Add(word);

        /// <summary>For tools/grammar-tests: a feminine stem added by hand (hard, soft, or on a consonant).</summary>
        public static void AddFeminineStem(string stem, bool soft = false, bool third = false) =>
            (third ? ThirdDeclension : soft ? SoftFeminine : HardFeminine).Add(stem);

        /// <summary>For tools/grammar-tests: a masculine plural's stem added by hand.</summary>
        public static void AddMasculinePluralStem(string stem) => MasculinePlural.Add(stem);
    }
}
