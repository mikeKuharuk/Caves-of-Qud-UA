// Ukrainian grammar that needs nothing from the game: the choice of a form by number, person or gender.
// Kept free of game types so that tools/grammar-tests can run it without Unity.
namespace CavesOfQudUA.Grammar
{
    /// <summary>Grammatical gender, with the plural as a fourth agreement class.</summary>
    public enum UkGender { Masculine, Feminine, Neuter, Plural }

    public static class UkrainianForms
    {
        /// <summary>Which of the three plural forms a number takes: 1 → 0 (хід), 2–4 → 1 (ходи), 5+ → 2 (ходів).</summary>
        public static int PluralIndex(long number)
        {
            long n = number < 0 ? -number : number;
            long lastTwo = n % 100, last = n % 10;
            if (lastTwo >= 11 && lastTwo <= 14) return 2;
            if (last == 1) return 0;
            if (last >= 2 && last <= 4) return 1;
            return 2;
        }

        /// <summary>The form for a number. With fewer than three forms the last one given stands in for the missing ones.</summary>
        public static string ByNumber(long number, string[] forms)
        {
            if (forms == null || forms.Length == 0) return "";
            int i = PluralIndex(number);
            return forms[i < forms.Length ? i : forms.Length - 1];
        }

        /// <summary>
        /// The form for a gender, from forms given as masculine:feminine:neuter:plural. A missing neuter falls back to
        /// the masculine, a missing plural to the last form given.
        /// </summary>
        public static string ByGender(UkGender gender, string[] forms)
        {
            if (forms == null || forms.Length == 0) return "";
            switch (gender)
            {
                case UkGender.Feminine: return forms.Length > 1 ? forms[1] : forms[0];
                case UkGender.Neuter: return forms.Length > 2 ? forms[2] : forms[0];
                case UkGender.Plural: return forms.Length > 3 ? forms[3] : forms[forms.Length - 1];
                default: return forms[0];
            }
        }

        /// <summary>
        /// ByGender, except that the player addressed as «ви» takes a fifth form when one is given: pronouns and
        /// possessives differ for the player («вас», «ваш») from the plural («їх», «їхній»).
        /// </summary>
        public static string ByGenderOrPlayer(bool secondPersonPlayer, UkGender gender, string[] forms)
        {
            if (secondPersonPlayer)
                return forms != null && forms.Length > 4 ? forms[4] : ByGender(UkGender.Plural, forms);
            return ByGender(gender, forms);
        }

        /// <summary>
        /// A present or future verb, from forms given as 3rd person singular:2nd person plural:3rd person plural.
        /// The player is always «ви» (D3), so the player takes the 2nd person plural; a plural subject takes the
        /// 3rd person plural when it is given.
        /// </summary>
        public static string ByPerson(bool isPlayer, bool isPlural, string[] forms)
        {
            if (forms == null || forms.Length == 0) return "";
            if (isPlayer) return forms.Length > 1 ? forms[1] : forms[0];
            if (isPlural && forms.Length > 2) return forms[2];
            return forms[0];
        }

        /// <summary>
        /// The agreement class of a gender name from the game (Genders.xml), or null when the name says nothing about
        /// Ukrainian grammar and the noun's own gender should decide.
        /// </summary>
        public static UkGender? FromGameGender(string name, bool plural, bool pseudoPlural)
        {
            switch (name)
            {
                case "male": return UkGender.Masculine;
                case "female": return UkGender.Feminine;
                case "plural": return UkGender.Plural;
                // ey/em of the mopango: the neuter where a gendered form is unavoidable (D11); "it" people likewise
                case "elverson":
                case "neuterperson": return UkGender.Neuter;
                // singular they: agreement in the plural, like the English (proposed to Mike, not yet decided)
                case "nonspecific": return UkGender.Plural;
                case "neuter": return null;
            }
            if (plural) return UkGender.Plural;
            if (pseudoPlural) return UkGender.Plural;
            return null;
        }

        /// <summary>A gender letter from the translation data (qud-gender: m, f, n, pl).</summary>
        public static UkGender? FromLetter(string letter)
        {
            switch (letter)
            {
                case "m": return UkGender.Masculine;
                case "f": return UkGender.Feminine;
                case "n": return UkGender.Neuter;
                case "pl": return UkGender.Plural;
            }
            return null;
        }

        /// <summary>
        /// An adjective agreed with a gender. text is the adjective as translated, in the masculine and possibly
        /// inside markup ({{K|іржавий}}); forms looks up the masculine plain text and gives [feminine, neuter,
        /// plural], or null when the adjective does not change (an indeclinable word, or not in the table).
        /// </summary>
        public static string AgreeAdjective(string text, UkGender gender, System.Func<string, string[]> forms)
        {
            if (string.IsNullOrEmpty(text) || gender == UkGender.Masculine || forms == null) return text;
            string plain = StripMarkup(text).Trim();
            string[] f = plain.Length == 0 ? null : forms(plain);
            if (f == null || f.Length < 3) return text;
            string form = gender == UkGender.Feminine ? f[0] : gender == UkGender.Neuter ? f[1] : f[2];
            if (string.IsNullOrEmpty(form)) return text;
            int at = text.IndexOf(plain, System.StringComparison.Ordinal);
            return at < 0 ? text : text.Substring(0, at) + form + text.Substring(at + plain.Length);
        }

        /// <summary>The text without Qud's {{shader|…}} markup and &amp;X / ^X colour codes.</summary>
        public static string StripMarkup(string text)
        {
            var sb = new System.Text.StringBuilder(text.Length);
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                if (c == '{' && i + 1 < text.Length && text[i + 1] == '{')
                {
                    int bar = text.IndexOf('|', i);
                    int close = text.IndexOf("}}", i, System.StringComparison.Ordinal);
                    if (bar > 0 && (close < 0 || bar < close)) { i = bar; continue; }
                }
                if (c == '}' && i + 1 < text.Length && text[i + 1] == '}') { i++; continue; }
                if ((c == '&' || c == '^') && i + 1 < text.Length && char.IsLetter(text[i + 1]) && text[i + 1] < 128) { i++; continue; }
                sb.Append(c);
            }
            return sb.ToString();
        }

        /// <summary>Upper-cases the first letter, leaving markup such as {{W|…}} alone.</summary>
        public static string Capitalize(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;
            int i = 0;
            while (i < text.Length)
            {
                if (text[i] == '{' && i + 1 < text.Length && text[i + 1] == '{')
                {
                    int bar = text.IndexOf('|', i);
                    if (bar < 0) return text;
                    i = bar + 1;
                    continue;
                }
                if (char.IsLetter(text[i]))
                    return text.Substring(0, i) + char.ToUpperInvariant(text[i]) + text.Substring(i + 1);
                i++;
            }
            return text;
        }
    }
}
