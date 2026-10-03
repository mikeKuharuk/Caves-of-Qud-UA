using System.Collections.Generic;

// Word tools the history generator uses on Ukrainian text: which words of a phrase carry meaning, a word's root.
// Free of game types, so tools/grammar-tests can run them.
namespace CavesOfQudUA.Grammar
{
    public static class UkrainianWordTools
    {
        // prepositions, conjunctions, particles and pronouns that never name anything
        static readonly HashSet<string> StopWords = new HashSet<string>
        {
            "і", "й", "та", "а", "але", "чи", "або", "що", "як", "бо", "щоб", "коли", "ні", "не", "же", "ж", "би", "б",
            "в", "у", "на", "до", "від", "з", "із", "зі", "зо", "за", "для", "про", "по", "над", "під", "при", "без",
            "через", "о", "об", "біля", "між", "серед", "крізь", "після", "перед", "поміж", "понад", "проти",
            "це", "цей", "ця", "ці", "той", "те", "ті", "його", "її", "їх", "їхній", "свій", "своя", "своє",
            "свої", "хто", "який", "яка", "яке", "які", "де", "там", "тут", "так", "вже", "ще", "лише", "тільки",
        };

        static string Bare(string word)
        {
            int start = 0, end = word.Length;
            while (start < end && !char.IsLetterOrDigit(word[start])) start++;
            while (end > start && !char.IsLetterOrDigit(word[end - 1])) end--;
            return word.Substring(start, end - start);
        }

        /// <summary>
        /// The words of a phrase that can stand for it: not stop words, and with three letters or more. When none
        /// qualifies, every word does (the game then picks any).
        /// </summary>
        public static List<string> MeaningfulWords(string phrase)
        {
            var all = new List<string>();
            var meaningful = new List<string>();
            foreach (string raw in (phrase ?? "").Split(' '))
            {
                string word = Bare(raw);
                if (word.Length == 0) continue;
                all.Add(word);
                if (word.Length >= 3 && !StopWords.Contains(word.ToLowerInvariant())) meaningful.Add(word);
            }
            return meaningful.Count > 0 ? meaningful : all;
        }

        static readonly string[] Endings =
        {
            "ського", "цького", "ового", "ьому", "ому", "ого", "ими", "ий", "ій", "їй", "ої", "ою", "их", "ім", "ам", "ах",
            "а", "я", "о", "е", "є", "и", "і", "ї", "у", "ю", "ь",
        };

        /// <summary>
        /// A word without its ending, to build a new word on (the game appends «град», «абад», «плац»): «Джоппа» →
        /// «Джопп», «мерехтливий» → «мерехтлив». At least three letters stay.
        /// </summary>
        public static string WordRoot(string word)
        {
            string w = Bare(word ?? "");
            foreach (string ending in Endings)
                if (w.Length - ending.Length >= 3 && w.EndsWith(ending, System.StringComparison.OrdinalIgnoreCase))
                    return w.Substring(0, w.Length - ending.Length);
            return w;
        }
    }
}
