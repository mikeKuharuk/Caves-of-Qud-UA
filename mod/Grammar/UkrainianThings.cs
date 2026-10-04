using System;
using System.Collections.Generic;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// The counts the game's code writes with Extensions.Things («5 turns», «1 dram»), in Ukrainian: «5 ходів»,
    /// «1 драм». The words are the literals the code passes (decompiled 2.0.212.31: 35 calls, 15 words). An English word
    /// not listed stays with the game. A Ukrainian one (MissileWeapon counts projectiles by their name) has no plural to
    /// give, so it is counted «стріла ×3» rather than «3 стріла».
    /// </summary>
    public static class UkrainianThings
    {
        sealed class Word
        {
            public readonly string Before;
            public readonly string[] Forms;

            public Word(string before, params string[] forms)
            {
                Before = before;
                Forms = forms;
            }
        }

        static readonly string[] Turns = { "хід", "ходи", "ходів" };

        static readonly Dictionary<string, Word> Words = new Dictionary<string, Word>
        {
            ["turn"] = new Word("", Turns),
            ["round"] = new Word("", Turns),
            // «N turns remain until …»: the translation brings the rest («Ще 5 ходів до …»)
            ["turn remains"] = new Word("", Turns),
            ["more turn"] = new Word("ще ", Turns),
            ["more round"] = new Word("ще ", Turns),
            ["square"] = new Word("", "клітинка", "клітинки", "клітинок"),
            ["dram"] = new Word("", "драм", "драми", "драмів"),
            ["child"] = new Word("", "дитина", "дитини", "дітей"),
            ["point"] = new Word("", "очко", "очки", "очок"),
            ["attribute point"] = new Word("", "очко характеристик", "очки характеристик", "очок характеристик"),
            ["mutation point"] = new Word("", "очко мутацій", "очки мутацій", "очок мутацій"),
            ["license point"] = new Word("", "очко ліцензії", "очки ліцензії", "очок ліцензії"),
            ["penetrating hit"] = new Word("", "пробивний удар", "пробивні удари", "пробивних ударів"),
            ["additional creature"] = new Word("", "додаткова істота", "додаткові істоти", "додаткових істот"),
        };

        /// <summary>
        /// «5 ходів» for the number (and its text, as the game prints it) and the English word the code passes, or null
        /// to leave it to the game. A number that is not whole takes the 2–4 form, the nearest to the genitive singular
        /// it needs («2,5 клітинки»).
        /// </summary>
        public static string Count(double number, string numberText, string what)
        {
            if (string.IsNullOrEmpty(what)) return null;
            if (Words.TryGetValue(what, out Word word))
            {
                bool whole = number == Math.Floor(number) && Math.Abs(number) < 1e15;
                int i = whole ? UkrainianForms.PluralIndex((long)number) : 1;
                return word.Before + numberText + " " + word.Forms[i];
            }
            foreach (char c in what)
                if (c >= 'Ѐ' && c <= 'ӿ') return what + " ×" + numberText;
            return null;
        }
    }
}
