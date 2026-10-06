using System.Collections.Generic;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// Words of the translation, in lower case, for UkrainianCases to read a name by: the masculine adjectives it uses
    /// («слоновий», «синій») and the nouns that stand alone as a name («мавпа», «дочка»). `py tools/qud.py build` fills
    /// them into AdjectiveLexicon.g.cs (commands.adjective_lexicon, noun_lexicon); without that file both are empty.
    /// «слонова» is an adjective, «слоновий» being in here; «дочка» is a noun.
    /// </summary>
    public static partial class AdjectiveLexicon
    {
        static readonly HashSet<string> Words = new HashSet<string>();
        static readonly HashSet<string> NounWords = new HashSet<string>();

        static AdjectiveLexicon()
        {
            Fill(Words);
            FillNouns(NounWords);
        }

        static partial void Fill(HashSet<string> t);

        static partial void FillNouns(HashSet<string> t);

        public static bool Contains(string word) => word != null && Words.Contains(word);

        public static bool IsNoun(string word) => word != null && NounWords.Contains(word);

        /// <summary>For tools/grammar-tests: a word added by hand.</summary>
        public static void Add(string word) => Words.Add(word);

        /// <summary>For tools/grammar-tests: a noun added by hand.</summary>
        public static void AddNoun(string word) => NounWords.Add(word);
    }
}
