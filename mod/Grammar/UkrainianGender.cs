using System.Collections.Generic;
using XRL.World;
using XRL.World.Text;

namespace CavesOfQudUA.Grammar
{
    /// <summary>How a game object agrees in Ukrainian: past tense, adjectives, the verb's number.</summary>
    public static class UkrainianGender
    {
        /// <summary>
        /// The player addressed as «ви». The game switches this off for texts that tell of the player in the third
        /// person (murals, gospels: Grammar.AllowSecondPerson), and then the player agrees like any named character.
        /// </summary>
        public static bool IsSecondPerson(GameObject obj)
        {
            return obj != null && obj.IsPlayer() && XRL.Language.Grammar.AllowSecondPerson;
        }

        /// <summary>
        /// The agreement class of an object.
        /// <list type="number">
        /// <item>The player addressed as «ви»: the plural.</item>
        /// <item>A named character agrees with their own gender («Мір’ям пішла»), the player in the third person too.</item>
        /// <item>Anything else agrees with the grammatical gender of its Ukrainian name: a female snapjaw is still
        /// «пащеклац», so «пащеклац упав».</item>
        /// <item>Without either, the masculine.</item>
        /// </list>
        /// </summary>
        public static UkGender Of(GameObject obj)
        {
            if (obj == null) return UkGender.Masculine;
            if (IsSecondPerson(obj)) return UkGender.Plural;
            return OfName(obj);
        }

        /// <summary>
        /// The agreement class of an object's name, which is always in the third person: the adjectives before the
        /// player's name follow the player's gender («слизька мокра Марта»), not the plural of «ви».
        /// </summary>
        public static UkGender OfName(GameObject obj)
        {
            if (obj == null) return UkGender.Masculine;
            UkGender? personal = Personal(obj);
            UkGender? noun = Noun(obj.GetBlueprint(false));
            if (obj.HasProperName || obj.IsPlayer()) return personal ?? noun ?? UkGender.Masculine;
            return noun ?? personal ?? UkGender.Masculine;
        }

        /// <summary>
        /// The gender of a zone name, for the biome adjective the game puts before it: the whole name if a translator
        /// gave it a qud-gender note, else the name without its first words («слизька соляна пустеля» → «соляна
        /// пустеля»), else, for a one-word proper name such as a village, a guess from its ending. Null: unknown.
        /// </summary>
        public static UkGender? OfZoneName(string name)
        {
            string[] words = UkrainianForms.StripMarkup(name ?? "").Trim().Split(' ');
            for (int i = 0; i < words.Length; i++)
            {
                UkGender? gender = NounGenders.OfWord(string.Join(" ", words, i, words.Length - i));
                if (gender.HasValue) return gender;
            }
            return words.Length == 1 ? UkrainianForms.GuessByEnding(words[0]) : null;
        }

        /// <summary>
        /// The gender of a name the game passes as text (a body part, a faction, a stat): a translator's qud-gender
        /// note on the whole or its last words, a word from the code tables, else a guess from the ending of its
        /// first word that is no adjective («нічний зір» → «зір»: masculine); the masculine when nothing tells.
        /// </summary>
        public static UkGender OfText(string text)
        {
            if (string.IsNullOrEmpty(text)) return UkGender.Masculine;
            string plain = UkrainianForms.StripMarkup(text).Trim();
            return NounGenders.OfWord(plain) ?? CodeWords.GenderOf(plain) ?? OfZoneName(plain) ?? UkrainianCases.GuessGender(plain)
                   ?? UkGender.Masculine;
        }

        /// <summary>A noun the game passes with its own pronouns (a body part, an effect, a random official).</summary>
        public static UkGender Of(GenderedNoun noun)
        {
            return FromPronouns(noun.Pronouns) ?? UkGender.Masculine;
        }

        static UkGender? Personal(GameObject obj)
        {
            IPronounProvider pronouns = obj.GetPronounProvider();
            if (pronouns != null && !(pronouns is Gender)) return FromPronouns(pronouns);
            return FromPronouns(obj.GetGender());
        }

        /// <summary>
        /// Genders go by their name (UkrainianForms.FromGameGender). An explicit pronoun set follows its subjective
        /// pronoun; a neopronoun set such as xe/xem takes the neuter, as D11 and D12 decided.
        /// </summary>
        static UkGender? FromPronouns(IPronounProvider pronouns)
        {
            if (pronouns == null) return null;
            // a gender the table does not know («hindren female», a generated one) goes by its pronouns
            if (pronouns is Gender gender)
                return UkrainianForms.FromGameGender(gender.Name, gender.Plural, gender.PseudoPlural)
                       ?? (gender.Name == "neuter" ? null : FromSubjective(pronouns));
            return FromSubjective(pronouns);
        }

        static UkGender? FromSubjective(IPronounProvider pronouns)
        {
            switch (pronouns.Subjective)
            {
                case "he": return UkGender.Masculine;
                case "she": return UkGender.Feminine;
                case "they": return UkGender.Plural;
                case "it": return null;
            }
            return pronouns.Plural ? UkGender.Plural : UkGender.Neuter;
        }

        static UkGender? Noun(GameObjectBlueprint blueprint)
        {
            for (int depth = 0; blueprint != null && depth < 64; depth++, blueprint = blueprint.ShallowParent)
            {
                if (NounGenders.ByBlueprint.TryGetValue(blueprint.Name, out string letter))
                    return UkrainianForms.FromLetter(letter);
            }
            return null;
        }
    }

    /// <summary>
    /// The grammatical gender of each object's Ukrainian name, from the translators' qud-gender notes, and of the
    /// nouns the code passes as plain strings (a liquid's name), by their Ukrainian text. The tables are written by
    /// `py tools/qud.py build` into NounGenders.g.cs; without that file they stay empty.
    /// </summary>
    public static partial class NounGenders
    {
        public static readonly Dictionary<string, string> ByBlueprint = new Dictionary<string, string>();
        public static readonly Dictionary<string, string> ByWord = new Dictionary<string, string>();

        static NounGenders()
        {
            Fill(ByBlueprint);
            FillWords(ByWord);
        }

        static partial void Fill(Dictionary<string, string> table);

        static partial void FillWords(Dictionary<string, string> table);

        /// <summary>The gender of a translated noun given as text («{{B|вода}}» → feminine), or null.</summary>
        public static UkGender? OfWord(string text)
        {
            if (string.IsNullOrEmpty(text)) return null;
            string key = UkrainianForms.StripMarkup(text).Trim().ToLowerInvariant();
            return ByWord.TryGetValue(key, out string letter) ? UkrainianForms.FromLetter(letter) : null;
        }
    }
}
