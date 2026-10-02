using System.Collections.Generic;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// English words that the game's code passes into templates as they are: string literals, not string-table
    /// entries. =rank|uk.word= prints the Ukrainian word; =x|uk.agree#rank= agrees x with the word's gender.
    ///   PsychicHunterSystem: the rank of Ptoh's seekers, named as in the glimmer descriptions (скопи, луні, сови…)
    ///   EvilTwin: the prefixes of twins made by ShadeOil_Tonic ("Shadow"), EngulfingClones ("Refracted") and the
    ///     "Mini" wish (adjectives; |uk.agree then agrees them with the twin)
    /// </summary>
    public static class CodeWords
    {
        static readonly Dictionary<string, KeyValuePair<string, UkGender>> Words =
            new Dictionary<string, KeyValuePair<string, UkGender>>
            {
                { "Osprey", Word("Скопа", UkGender.Feminine) },
                { "Harrier", Word("Лунь", UkGender.Masculine) },
                { "Owl", Word("Сова", UkGender.Feminine) },
                { "Condor", Word("Кондор", UkGender.Masculine) },
                { "Strix", Word("Стрикс", UkGender.Masculine) },
                { "Eagle", Word("Орел", UkGender.Masculine) },
                { "Rukh", Word("Рух", UkGender.Masculine) },
                { "Shadow", Word("Тіньовий", UkGender.Masculine) },
                { "Refracted", Word("Заломлений", UkGender.Masculine) },
                { "Mini", Word("Міні-", UkGender.Masculine) },
            };

        static KeyValuePair<string, UkGender> Word(string ukrainian, UkGender gender)
        {
            return new KeyValuePair<string, UkGender>(ukrainian, gender);
        }

        /// <summary>The Ukrainian for a word from the code, or the word itself when it is not in the table.</summary>
        public static string Translate(string word)
        {
            return word != null && Words.TryGetValue(word, out KeyValuePair<string, UkGender> w) ? w.Key : word;
        }

        /// <summary>The gender of a word from the code, given in English or already translated; null if unknown.</summary>
        public static UkGender? GenderOf(string word)
        {
            if (string.IsNullOrEmpty(word)) return null;
            if (Words.TryGetValue(word, out KeyValuePair<string, UkGender> w)) return w.Value;
            foreach (KeyValuePair<string, UkGender> v in Words.Values)
                if (v.Key == word) return v.Value;
            return null;
        }
    }
}
