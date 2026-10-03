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
        /// The form of =X.p:<for the player>:<for anyone else>=: the first for the player addressed as «ви», the second
        /// (with @ for the name) for anyone else; a lone form serves the player, and anyone else gets just the name.
        /// </summary>
        public static string ForPlayerOrOther(bool secondPersonPlayer, string[] forms)
        {
            if (forms == null || forms.Length == 0) return secondPersonPlayer ? "" : "@";
            if (secondPersonPlayer) return forms[0];
            return forms.Length > 1 ? forms[1] : "@";
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
                // singular they: agreement in the plural, «вони», like the English (D12)
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
        /// A guess at the gender of a proper name from its ending, for names no translator annotated (a generated
        /// village): -а/-я feminine (Джоппа), -о/-е/-є neuter, -и/-і/-ї plural, a consonant masculine (Туркатум).
        /// Null for -ь and anything else, where the ending does not tell.
        /// </summary>
        public static UkGender? GuessByEnding(string word)
        {
            string w = StripMarkup(word ?? "").Trim().ToLowerInvariant();
            if (w.Length < 2 || !char.IsLetter(w[w.Length - 1])) return null;
            switch (w[w.Length - 1])
            {
                case 'а': case 'я': return UkGender.Feminine;
                case 'о': case 'е': case 'є': return UkGender.Neuter;
                case 'и': case 'і': case 'ї': return UkGender.Plural;
                case 'ь': return null;
            }
            return w[w.Length - 1] >= 'а' && w[w.Length - 1] <= 'я' || w[w.Length - 1] == 'ґ' ? UkGender.Masculine : (UkGender?)null;
        }

        /// <summary>
        /// An adjective agreed with a gender. text is the adjective as translated, in the masculine and possibly
        /// inside markup ({{K|іржавий}}); forms looks up the masculine plain text and gives [feminine, neuter,
        /// plural], or null when the adjective does not change (an indeclinable word, or not in the table).
        /// Two adjectives joined by «і», «й», «та» or a comma («заплямований кров’ю і заплямований вином») agree one
        /// by one. With regular, an adjective missing from the table takes the regular endings (InflectRegular).
        /// </summary>
        public static string AgreeAdjective(string text, UkGender gender, System.Func<string, string[]> forms,
                                            bool regular = false)
        {
            if (string.IsNullOrEmpty(text) || gender == UkGender.Masculine) return text;
            string plain = StripMarkup(text).Trim();
            if (plain.Length == 0) return text;
            string whole = FromTable(plain, gender, forms);
            if (whole != null) return Replace(text, plain, whole, 0, out _);
            string[] parts = plain.Split(Joints, System.StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return regular ? InflectRegular(text, gender) : text;
            string result = text;
            int from = 0;
            foreach (string raw in parts)
            {
                string part = raw.Trim();
                string form = FromTable(part, gender, forms) ?? (regular ? InflectRegular(part, gender) : part);
                result = Replace(result, part, form, from, out from);
            }
            return result;
        }

        static readonly string[] Joints = { " і ", " й ", " та ", ", " };

        static string FromTable(string plain, UkGender gender, System.Func<string, string[]> forms)
        {
            string[] f = forms == null ? null : forms(plain);
            if (f == null || f.Length < 3) return null;
            string form = gender == UkGender.Feminine ? f[0] : gender == UkGender.Neuter ? f[1] : f[2];
            return string.IsNullOrEmpty(form) ? null : form;
        }

        // replaces the first plain after from in text (plain appears there whole, inside markup if any)
        static string Replace(string text, string plain, string form, int from, out int end)
        {
            int at = text.IndexOf(plain, from, System.StringComparison.Ordinal);
            if (at < 0)
            {
                end = from;
                return text;
            }
            end = at + form.Length;
            return text.Substring(0, at) + form + text.Substring(at + plain.Length);
        }

        static readonly System.Text.RegularExpressions.Regex RegularAdjective = new System.Text.RegularExpressions.Regex(
            @"(?<![\p{L}’'ʼ-])([\p{L}’'ʼ-]*?\p{L})(ий|ій|їй)(?![\p{L}’'ʼ])");
        static readonly System.Text.RegularExpressions.Regex DigitOrdinal = new System.Text.RegularExpressions.Regex(
            @"(?<![\d])(-?\d+)-й(?!\p{L})");

        /// <summary>
        /// A masculine adjective phrase agreed by the regular endings, for adjectives with no uk-forms note:
        /// -ий → -а/-е/-і (сірий), -ій → -я/-є/-і (синій), -їй → -я/-є/-ї (безкраїй). An ordinal in digits takes its
        /// ending from the numeral: 1-й → 1-ша, 2-й → 2-га, 3-й → 3-тя, 7-й → 7-ма, 10-й → 10-та. Every such word in text
        /// changes (a phrase such as «вкритий кислотою» agrees); markup stays.
        /// </summary>
        public static string InflectRegular(string text, UkGender gender)
        {
            if (string.IsNullOrEmpty(text) || gender == UkGender.Masculine) return text;
            int g = gender == UkGender.Feminine ? 0 : gender == UkGender.Neuter ? 1 : 2;
            text = RegularAdjective.Replace(text, m =>
            {
                string stem = m.Groups[1].Value;
                switch (m.Groups[2].Value)
                {
                    case "ий": return stem + new[] { "а", "е", "і" }[g];
                    case "ій": return stem + new[] { "я", "є", "і" }[g];
                    default: return stem + new[] { "я", "є", "ї" }[g];
                }
            });
            return DigitOrdinal.Replace(text, m => m.Groups[1].Value + "-" + OrdinalEnding(long.Parse(m.Groups[1].Value), g));
        }

        // the letters after the hyphen of an ordinal in digits, feminine/neuter/plural by g, from the numeral's last word
        static string OrdinalEnding(long number, int g)
        {
            long n = number < 0 ? -number : number;
            string stem;
            if (n == 0) stem = "в";                                   // нульова
            else if (n % 100 >= 10 && n % 100 <= 19) stem = "т";      // десята, одинадцята
            else if (n % 1000 == 0) stem = "н";                       // тисячна
            else if (n % 100 == 40) stem = "в";                       // сорокова
            else if (n % 10 == 0) stem = "т";                         // двадцята, сота
            else
            {
                switch (n % 10)
                {
                    case 1: stem = "ш"; break;                        // перша
                    case 2: stem = "г"; break;                        // друга
                    case 3: return new[] { "тя", "тє", "ті" }[g];     // третя
                    case 7:
                    case 8: stem = "м"; break;                        // сьома, восьма
                    default: stem = "т"; break;                       // четверта, п’ята, шоста, дев’ята
                }
            }
            return stem + new[] { "а", "е", "і" }[g];
        }

        /// <summary>
        /// Text the .NET culture formatted (a date), in our typography: the apostrophe ’ instead of ʼ («пʼятниця») or ',
        /// and plain spaces instead of the no-break ones before «р.», which the game's fonts may lack.
        /// </summary>
        public static string CleanCultureText(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;
            return text.Replace('ʼ', '’').Replace('\'', '’').Replace(' ', ' ').Replace(' ', ' ');
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
