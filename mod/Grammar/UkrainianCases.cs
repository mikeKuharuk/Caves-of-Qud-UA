using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;

namespace CavesOfQudUA.Grammar
{
    public enum UkCase { Nominative, Genitive, Dative, Accusative, Instrumental, Locative }

    /// <summary>
    /// A name in a case (=object.n:acc=, docs/grammar.md): «шкіряна броня» → «шкіряну броню», «пащеклац» → «пащеклаца»,
    /// «пляшка води» → «пляшку води». The name's leading adjectives and its head noun change; what follows the head (a
    /// genitive, a preposition, brackets, «Mk I») stays. An adjective is a word whose masculine form the translation
    /// uses somewhere (Lexicon, from tools/qudtr: «слонова» because «слоновий»); words with alternations and other
    /// irregular nouns come from a table (Irregular). Markup stays where it was: «{{W|фугасна}} граната» →
    /// «{{W|фугасну}} гранату». A name this cannot read stays as it is.
    /// </summary>
    public static class UkrainianCases
    {
        /// <summary>The masculine adjectives the translation uses («слоновий», «синій»); empty until the mod fills it.</summary>
        public static Func<string, bool> Lexicon = AdjectiveLexicon.Contains;

        /// <summary>Multi-word adjectives with their forms, masculine → [feminine, neuter, plural] («вкритий лавою»).</summary>
        public static Func<IEnumerable<KeyValuePair<string, string[]>>> PhraseAdjectives =
            () => new KeyValuePair<string, string[]>[0];

        public static UkCase? Parse(string key)
        {
            switch ((key ?? "").Trim().ToLowerInvariant())
            {
                case "nom": return UkCase.Nominative;
                case "gen": return UkCase.Genitive;
                case "dat": return UkCase.Dative;
                case "acc": return UkCase.Accusative;
                case "ins": return UkCase.Instrumental;
                case "loc": return UkCase.Locative;
            }
            return null;
        }

        /// <summary>
        /// A guess at the gender of a name by its noun: the ending of its first word that is not an adjective of any
        /// gender («нічний зір» → «зір», «Відомі модифікації» → plural). Null when no word tells.
        /// </summary>
        public static UkGender? GuessGender(string name)
        {
            List<Token> tokens = Tokens(name ?? "", out string _);
            UkGender[] genders = { UkGender.Masculine, UkGender.Feminine, UkGender.Neuter, UkGender.Plural };
            string last = null;
            foreach (Token t in tokens)
            {
                if (!IsCyrillic(t)) break;
                string word = Last(t);
                if (Prepositions.Contains(word.ToLowerInvariant())) break;
                last = word;
                bool adjective = false;
                foreach (UkGender g in genders) adjective |= IsAdjective(word, g);
                if (!adjective) return UkrainianForms.GuessByEnding(word);
            }
            if (last == null) return null;
            // only adjectives: «черговий», «Відомі»
            foreach (UkGender g in genders)
                if (IsAdjective(last, g)) return g;
            return null;
        }

        /// <summary>The player, «ви», in a case.</summary>
        public static string You(UkCase c)
        {
            switch (c)
            {
                case UkCase.Dative: return "вам";
                case UkCase.Instrumental: return "вами";
                case UkCase.Nominative: return "ви";
                default: return "вас";
            }
        }

        // ---- the name's words ---------------------------------------------------------------------------------------

        sealed class Part { public int Start, End; public string Text; }        // a word between hyphens, in the original
        sealed class Token { public readonly List<Part> Parts = new List<Part>(); public int PlainStart, PlainEnd; }

        static readonly Regex WordInPlain = new Regex(@"[\p{L}\d’'ʼ]+(?:-[\p{L}\d’'ʼ]+)*");
        static readonly Regex Cyrillic = new Regex(@"\p{IsCyrillic}");

        /// <summary>The name in case c, for a name of gender (the head noun's) on an animate or inanimate object.</summary>
        public static string Inflect(string name, UkGender gender, bool animate, UkCase c)
        {
            if (string.IsNullOrEmpty(name) || c == UkCase.Nominative) return name;
            try
            {
                List<Token> tokens = Tokens(name, out string plain);
                if (tokens.Count == 0 || !IsCyrillic(tokens[0])) return name;
                // a list of things («глина, металева обшивка й тканина») has no one head
                if (gender == UkGender.Plural && plain.IndexOf(',') >= 0) return name;
                int head = Analyse(tokens, plain, gender, out List<int> adjectives, out Dictionary<int, int> units);
                if (head < 0) return name;
                // a plural name whose head is not a plural («Мімік і скаженоголовок») stays as it is
                if (gender == UkGender.Plural && !PluralForm(Last(tokens[head]))) return name;
                // two things joined («Злочин і кара») would want both declined: they stay as they are
                if (head + 1 < tokens.Count && Conjunctions.Contains(Last(tokens[head + 1]).ToLowerInvariant())) return name;
                var edits = new List<KeyValuePair<Part, string>>();
                foreach (int a in adjectives)
                {
                    // an adjective of several words declines its first (вкрита лавою), a hyphenated one its last
                    Token t = tokens[a];
                    Part p = units.ContainsKey(a) ? t.Parts[0] : t.Parts[t.Parts.Count - 1];
                    edits.Add(new KeyValuePair<Part, string>(p, Adjective(p.Text, gender, animate, c)));
                }
                // each part of a compound in its own declension: «херувима-квітку», «голема-козу»
                List<Part> parts = tokens[head].Parts;
                for (int k = 0; k < parts.Count; k++)
                {
                    Part p = parts[k];
                    // a prefix before a hyphen stays: «гамма-метелика», «шеф-кухаря»
                    if (k < parts.Count - 1 && InvariablePrefixes.Contains(p.Text.ToLowerInvariant())) continue;
                    if (!Declinable(p.Text, gender)) continue;
                    // an adjective that names a thing declines as one: «вартового», «колісничого», «Багатоокого»
                    string form = Substantive(p.Text) ? Adjective(p.Text, UkGender.Masculine, animate, c) : Noun(p.Text, gender, animate, c);
                    edits.Add(new KeyValuePair<Part, string>(p, form));
                }
                edits.Sort((x, y) => y.Key.Start.CompareTo(x.Key.Start));
                var sb = new StringBuilder(name);
                foreach (var e in edits)
                {
                    sb.Remove(e.Key.Start, e.Key.End - e.Key.Start);
                    sb.Insert(e.Key.Start, e.Value);
                }
                return sb.ToString();
            }
            catch (Exception)
            {
                return name;   // a name this cannot read stays as it is
            }
        }

        // the words of name, read without its markup; each word part keeps its place in name
        static List<Token> Tokens(string name, out string plain)
        {
            var map = new List<int>(name.Length);
            var sb = new StringBuilder(name.Length);
            for (int i = 0; i < name.Length; i++)
            {
                char ch = name[i];
                if (ch == '{' && i + 1 < name.Length && name[i + 1] == '{')
                {
                    int bar = name.IndexOf('|', i);
                    int close = name.IndexOf("}}", i, StringComparison.Ordinal);
                    if (bar > 0 && (close < 0 || bar < close)) { i = bar; continue; }
                }
                if (ch == '}' && i + 1 < name.Length && name[i + 1] == '}') { i++; continue; }
                if ((ch == '&' || ch == '^') && i + 1 < name.Length && char.IsLetter(name[i + 1]) && name[i + 1] < 128) { i++; continue; }
                map.Add(i);
                sb.Append(ch);
            }
            plain = sb.ToString();
            var tokens = new List<Token>();
            foreach (Match m in WordInPlain.Matches(plain))
            {
                var t = new Token { PlainStart = m.Index, PlainEnd = m.Index + m.Length };
                int from = m.Index;
                foreach (string piece in m.Value.Split('-'))
                {
                    int start = map[from], end = map[from + piece.Length - 1] + 1;
                    // a word part must sit whole in the original (markup only ever comes between words)
                    if (end - start != piece.Length) return new List<Token>();
                    t.Parts.Add(new Part { Start = start, End = end, Text = piece });
                    from += piece.Length + 1;
                }
                tokens.Add(t);
            }
            return tokens;
        }

        static bool IsCyrillic(Token t) => Cyrillic.IsMatch(t.Parts[t.Parts.Count - 1].Text);

        static bool Contiguous(List<Token> tokens, string plain, int i) =>
            i == 0 || plain.Substring(tokens[i - 1].PlainEnd, tokens[i].PlainStart - tokens[i - 1].PlainEnd).Trim().Length == 0;

        static readonly HashSet<string> Conjunctions = new HashSet<string> { "і", "й", "та", "чи", "або", "and" };

        static readonly HashSet<string> Prepositions = new HashSet<string>
        {
            "від", "з", "із", "зі", "у", "в", "уві", "на", "по", "для", "до", "без", "під", "над", "біля", "поміж", "між",
            "за", "через", "про", "при", "проти", "серед", "крізь", "попід", "понад",
        };

        /// <summary>
        /// The head noun's token (or -1), the adjectives before it, and which of those are several words (their first
        /// token → how many). Between an adjective and the head may stand its complement: an instrumental («поїдена
        /// іржею пилка») or a preposition with its noun («вологі від кислоти ікла»).
        /// </summary>
        static int Analyse(List<Token> tokens, string plain, UkGender gender, out List<int> adjectives, out Dictionary<int, int> units)
        {
            adjectives = new List<int>();
            units = new Dictionary<int, int>();
            if (tokens.Count == 1) return 0;   // a single word is the noun («Андрій», «сірий» as a name)
            int i = 0;
            while (i < tokens.Count && IsCyrillic(tokens[i]) && Contiguous(tokens, plain, i))
            {
                int unit = PhraseAdjective(tokens, plain, i, gender);
                if (unit > 1)
                {
                    adjectives.Add(i);
                    units[i] = unit;
                    i += unit;
                    continue;
                }
                string word = Last(tokens[i]);
                if ((IsAdjective(word, gender) && !HeadBeforeGenitive(tokens, plain, i, gender)) || AgreesBeforeNoun(tokens, plain, i, gender))
                {
                    adjectives.Add(i);
                    i++;
                    continue;
                }
                // an adverb before an adjective: «пишно гравіровані двері»
                if (IsAdverb(tokens, plain, i, gender))
                {
                    i++;
                    continue;
                }
                if (adjectives.Count > 0 && IsComplement(word, gender))
                {
                    i++;
                    continue;
                }
                if (adjectives.Count > 0 && Prepositions.Contains(word.ToLowerInvariant()) && i + 1 < tokens.Count)
                {
                    i += 2;
                    continue;
                }
                // a title that opens with a preposition («Про мімікрію…», «За модулем…») has no head to decline
                if (adjectives.Count == 0 && Prepositions.Contains(word.ToLowerInvariant())) return -1;
                return i;
            }
            if (adjectives.Count == 0) return -1;
            // nothing after the adjectives: the last of them is the noun («черговий»)
            int last = adjectives[adjectives.Count - 1];
            adjectives.RemoveAt(adjectives.Count - 1);
            units.Remove(last);
            return last;
        }

        static string Last(Token t) => t.Parts[t.Parts.Count - 1].Text;

        /// <summary>
        /// A word the lexicon does not know, with an adjective's ending, before a noun with a nominative's: an
        /// adjective too («груба тога», «заземлювальні шунти»), unless the lexicon knows it as a noun («дочка
        /// фермера»). Masculine needs none of this: its adjectives end in -ий, -ій.
        /// </summary>
        static bool AgreesBeforeNoun(List<Token> tokens, string plain, int i, UkGender gender)
        {
            if (gender == UkGender.Masculine || i + 1 >= tokens.Count || !Contiguous(tokens, plain, i + 1) || !IsCyrillic(tokens[i + 1]))
                return false;
            string word = Last(tokens[i]), following = Last(tokens[i + 1]);
            string w = word.ToLowerInvariant();
            if (w.Length < 3 || AdjectiveLexicon.IsNoun(w)) return false;
            // a proper name after a common word is its genitive («сторінка Шредінгера»), not a noun it agrees with
            if (char.IsLower(word[0]) && char.IsUpper(following[0])) return false;
            string next = following.ToLowerInvariant();
            // a neuter verbal noun (становлення, буття) follows a feminine noun in the genitive, never its adjective
            if (gender == UkGender.Feminine && EndsAny(next, "ння", "ття", "ддя", "ззя", "сся", "лля")) return false;
            switch (gender)
            {
                case UkGender.Feminine:
                    // -ка ends a noun (дочка, зупинка, коробка) far more often than an adjective the lexicon lacks
                    if (w.EndsWith("ка") && !EndsAny(w, "ська", "цька", "зька")) return false;
                    // the noun may be one on a consonant: «слонова кість», «гвинтівкова турель»
                    return EndsAny(w, "а", "я") && EndsAny(next, "а", "я", "ь");
                case UkGender.Neuter: return EndsAny(w, "е", "є") && EndsAny(next, "о", "е", "є", "я");
                default: return EndsAny(w, "і", "ї") && EndsAny(next, "и", "і", "ї", "а", "я");
            }
        }

        // a feminine that looks like an adjective but has a genitive after it is the noun: «в’язка шумотрави» (no
        // feminine noun in the nominative ends in -и, -і; its complement or preposition would be no genitive)
        static bool HeadBeforeGenitive(List<Token> tokens, string plain, int i, UkGender gender)
        {
            if (i + 1 >= tokens.Count || !Contiguous(tokens, plain, i + 1) || !IsCyrillic(tokens[i + 1])) return false;
            string next = Last(tokens[i + 1]);
            string n = next.ToLowerInvariant();
            // «вартовий Святилища»: a proper name in the genitive after an adjective that names a person
            if (gender == UkGender.Masculine)
                return char.IsLower(Last(tokens[i])[0]) && char.IsUpper(next[0]) && EndsAny(n, "а", "я", "у", "ю", "и", "і", "ї");
            if (gender != UkGender.Feminine) return false;
            if (!EndsAny(n, "и", "і", "ї") || IsComplement(next, gender) || Prepositions.Contains(n)) return false;
            return !IsAdjective(next, gender) && !EndsAny(n, "ої", "ьої", "йої");
        }

        // a word on -о before an adjective modifies it («пишно гравіровані»): no noun stands before its adjective
        static bool IsAdverb(List<Token> tokens, string plain, int i, UkGender gender)
        {
            string w = Last(tokens[i]);
            if (w.Length < 4 || !w.EndsWith("о") || char.IsUpper(w[0]) || tokens[i].Parts.Count > 1) return false;
            if (i + 1 >= tokens.Count || !Contiguous(tokens, plain, i + 1) || !IsCyrillic(tokens[i + 1])) return false;
            return IsAdjective(Last(tokens[i + 1]), gender) || AgreesBeforeNoun(tokens, plain, i + 1, gender);
        }

        static bool EndsAny(string word, params string[] endings)
        {
            foreach (string e in endings)
                if (word.EndsWith(e)) return true;
            return false;
        }

        // an instrumental never names a thing in the nominative: «іржею», «шипами»; nor, before a noun that is not
        // masculine, a masculine one: «обліплені дьогтем кістки» (a masculine noun may end so: «шолом», «херувим»)
        static bool IsComplement(string word, UkGender gender)
        {
            string w = word.ToLowerInvariant();
            if (EndsAny(w, "ою", "ею", "єю", "ами", "ями")) return true;
            return gender != UkGender.Masculine && w.Length > 3 && EndsAny(w, "ом", "ем", "єм", "им", "ім");
        }

        static int PhraseAdjective(List<Token> tokens, string plain, int i, UkGender gender)
        {
            int best = 0;
            foreach (var pair in PhraseAdjectives())
            {
                string form = gender == UkGender.Masculine ? pair.Key : FormFor(pair.Value, gender);
                if (string.IsNullOrEmpty(form)) continue;
                string[] words = form.Split(' ');
                if (words.Length < 2 || words.Length <= best || i + words.Length > tokens.Count) continue;
                bool match = true;
                for (int k = 0; k < words.Length && match; k++)
                    match = Contiguous(tokens, plain, i + k) && string.Equals(Text(tokens[i + k]), words[k], StringComparison.OrdinalIgnoreCase);
                if (match) best = words.Length;
            }
            return best;
        }

        static string FormFor(string[] forms, UkGender gender)
        {
            if (forms == null || forms.Length < 3) return null;
            return gender == UkGender.Feminine ? forms[0] : gender == UkGender.Neuter ? forms[1] : forms[2];
        }

        static string Text(Token t)
        {
            var sb = new StringBuilder();
            foreach (Part p in t.Parts)
            {
                if (sb.Length > 0) sb.Append('-');
                sb.Append(p.Text);
            }
            return sb.ToString();
        }

        static readonly Regex OrdinalDigits = new Regex(@"^\d+$");

        /// <summary>Whether word is an adjective of gender in the nominative: by its ending and the lexicon.</summary>
        public static bool IsAdjective(string word, UkGender gender)
        {
            string w = (word ?? "").ToLowerInvariant();
            if (w.Length < 3) return false;
            // -ський, -цький, -зький make adjectives only: «пасажирська консоль», «екуемекійська зелень»
            string ending = gender == UkGender.Feminine ? "а" : gender == UkGender.Neuter ? "е" : gender == UkGender.Plural ? "і" : "ий";
            if (EndsAny(w, "ськ" + ending, "цьк" + ending, "зьк" + ending)) return true;
            switch (gender)
            {
                case UkGender.Masculine:
                    // релікварій, санаторій: nouns
                    return (w.EndsWith("ий") || w.EndsWith("ій") || w.EndsWith("їй")) && !NounsLikeAdjectives.Contains(w)
                           && !w.EndsWith("арій") && !w.EndsWith("орій");
                case UkGender.Feminine:
                    if (w.EndsWith("а")) return Lexicon(w.Substring(0, w.Length - 1) + "ий");
                    if (w.EndsWith("я")) return Lexicon(w.Substring(0, w.Length - 1) + "ій") || Lexicon(w.Substring(0, w.Length - 1) + "їй");
                    return false;
                case UkGender.Neuter:
                    if (w.EndsWith("е")) return Lexicon(w.Substring(0, w.Length - 1) + "ий");
                    if (w.EndsWith("є")) return Lexicon(w.Substring(0, w.Length - 1) + "ій") || Lexicon(w.Substring(0, w.Length - 1) + "їй");
                    return false;
                default:
                    if (w.EndsWith("і")) return Lexicon(w.Substring(0, w.Length - 1) + "ий") || Lexicon(w.Substring(0, w.Length - 1) + "ій");
                    if (w.EndsWith("ї")) return Lexicon(w.Substring(0, w.Length - 1) + "їй");
                    return false;
            }
        }

        // loanwords that never change though their ending would
        static readonly HashSet<string> Indeclinable = new HashSet<string>
        {
            "мопанго", "пончо", "манго", "кімоно", "сомбреро", "желе", "пюре", "кафе", "кашне", "шимпанзе", "фойє", "кенгуру",
            "реле", "пальто", "трико", "тако", "уне",
        };

        static readonly HashSet<string> NounsLikeAdjectives = new HashSet<string> { "змій", "буревій", "водій", "кий", "рій", "гній", "палій" };

        // the first part of a compound that never changes: «гамма-метелика», «шеф-кухаря»
        static readonly HashSet<string> InvariablePrefixes = new HashSet<string>
        {
            "гамма", "альфа", "бета", "дельта", "омега", "сигма", "тета", "лямбда", "каппа", "епсилон", "шеф", "віце", "екс",
            "міні", "максі", "ультра", "супер", "гіпер", "мета", "прото", "псевдо", "квазі",
        };

        // a word that changes: Cyrillic, not an abbreviation (ЕМІ) or a letter (к-), not a word that never declines (алое,
        // мопанго); -и, -і end a plural, and a singular noun only that never declines (іссахарі-)
        static bool Declinable(string word, UkGender gender)
        {
            if (string.IsNullOrEmpty(word) || word.Length < 3 || !Cyrillic.IsMatch(word)) return false;
            if (word == word.ToUpperInvariant()) return false;
            string w = word.ToLowerInvariant();
            char last = w[w.Length - 1];
            if (Indeclinable.Contains(w)) return false;
            if (last == 'у' || last == 'ю') return false;
            if ((last == 'і' || last == 'и' || last == 'ї') && gender != UkGender.Plural) return false;
            // a vowel (or й) before the last one: a loanword that never changes (радіо, алое, моа, Ґям’йо)
            if ((last == 'о' || last == 'е' || last == 'є' || last == 'а') && "аоеиіуюяєїй".IndexOf(w[w.Length - 2]) >= 0) return false;
            // a masculine on -е is a foreign name (Фіне, Спарафучіле)
            if (gender == UkGender.Masculine && (last == 'е' || last == 'є')) return false;
            return true;
        }

        // a plural noun's ending: «роги», «кігті», «жвала», «поля»
        static bool PluralForm(string word) => EndsAny(word.ToLowerInvariant(), "и", "і", "ї", "а", "я");

        /// <summary>An adjective that names a thing (вартовий, колісничий, Багатоокий): it declines as an adjective.</summary>
        static bool Substantive(string word)
        {
            string w = word.ToLowerInvariant();
            if (w.Length < 4 || NounsLikeAdjectives.Contains(w)) return false;
            if (w.EndsWith("ий")) return true;
            // on -ій only a soft adjective the translation knows (not Андрій, адій)
            return (w.EndsWith("ій") || w.EndsWith("їй")) && char.IsLower(word[0]) && Lexicon(w);
        }

        // soft adjectives (синій → сині → синіх), for a plural the lexicon cannot tell
        static readonly HashSet<string> SoftAdjectives = new HashSet<string>
        {
            "синій", "верхній", "нижній", "середній", "задній", "передній", "крайній", "останній", "давній", "древній",
            "ранній", "пізній", "вечірній", "літній", "осінній", "сусідній", "справжній", "внутрішній", "зовнішній",
            "домашній", "колишній", "третій", "кутній",
        };

        // ---- adjectives ---------------------------------------------------------------------------------------------

        /// <summary>An adjective in the nominative of gender, in case c (an animate masculine or plural takes the
        /// genitive for the accusative).</summary>
        public static string Adjective(string word, UkGender gender, bool animate, UkCase c)
        {
            string w = word;
            string lower = w.ToLowerInvariant();
            if (c == UkCase.Accusative && (gender == UkGender.Masculine || gender == UkGender.Plural))
                return animate ? Adjective(word, gender, animate, UkCase.Genitive) : word;
            switch (gender)
            {
                case UkGender.Masculine:
                    if (lower.EndsWith("ий")) return Swap(w, 2, Pick(c, "ого", "ому", null, "им", "ому"));
                    if (lower.EndsWith("їй")) return Swap(w, 2, Pick(c, "його", "йому", null, "їм", "йому"));
                    if (lower.EndsWith("ій")) return Swap(w, 2, Pick(c, "ього", "ьому", null, "ім", "ьому"));
                    return word;
                case UkGender.Feminine:
                    if (lower.EndsWith("ая") || lower.EndsWith("яя")) return Swap(w, 1, Pick(c, "йої", "їй", "ю", "йою", "їй"));
                    if (lower.EndsWith("я")) return Swap(w, 1, Pick(c, "ьої", "ій", "ю", "ьою", "ій"));
                    if (lower.EndsWith("а")) return Swap(w, 1, Pick(c, "ої", "ій", "у", "ою", "ій"));
                    return word;
                case UkGender.Neuter:
                    if (c == UkCase.Accusative) return word;
                    if (lower.EndsWith("є")) return Swap(w, 1, Pick(c, "ього", "ьому", null, "ім", "ьому"));
                    if (lower.EndsWith("е")) return Swap(w, 1, Pick(c, "ого", "ому", null, "им", "ому"));
                    return word;
                default:
                    if (lower.EndsWith("ї")) return Swap(w, 1, Pick(c, "їх", "їм", null, "їми", "їх"));
                    if (lower.EndsWith("і"))
                    {
                        string masculine = lower.Substring(0, lower.Length - 1);
                        bool soft = SoftAdjectives.Contains(masculine + "ій") || Lexicon(masculine + "ій") && !Lexicon(masculine + "ий");
                        return soft ? Swap(w, 1, Pick(c, "іх", "ім", null, "іми", "іх")) : Swap(w, 1, Pick(c, "их", "им", null, "ими", "их"));
                    }
                    return word;
            }
        }

        // the ending for case c from the forms of gen, dat, acc, ins, loc (null: the word itself)
        static string Pick(UkCase c, string gen, string dat, string acc, string ins, string loc)
        {
            switch (c)
            {
                case UkCase.Genitive: return gen;
                case UkCase.Dative: return dat;
                case UkCase.Accusative: return acc;
                case UkCase.Instrumental: return ins;
                case UkCase.Locative: return loc;
            }
            return null;
        }

        // word with its last n letters replaced by ending (null ending: the word as it is)
        static string Swap(string word, int n, string ending)
        {
            if (ending == null) return word;
            string stem = word.Substring(0, word.Length - n);
            bool upper = word.Length > 1 && word == word.ToUpperInvariant();
            return stem + (upper ? ending.ToUpperInvariant() : ending);
        }

        // ---- nouns --------------------------------------------------------------------------------------------------

        /// <summary>Irregular nouns: the nominative → genitive, dative, accusative, instrumental, locative.</summary>
        public static readonly Dictionary<string, string[]> Irregular = new Dictionary<string, string[]>
        {
            // a vowel that changes in the last syllable (і → о, е), a vowel that drops
            { "ніж", new[] { "ножа", "ножу", "ніж", "ножем", "ножі" } },
            { "кіт", new[] { "кота", "котові", "кота", "котом", "котові" } },
            { "віл", new[] { "вола", "волові", "вола", "волом", "волові" } },
            { "кінь", new[] { "коня", "коневі", "коня", "конем", "коневі" } },
            { "камінь", new[] { "каменя", "каменю", "камінь", "каменем", "камені" } },
            { "вогонь", new[] { "вогню", "вогню", "вогонь", "вогнем", "вогні" } },
            { "ремінь", new[] { "ременя", "ременю", "ремінь", "ременем", "ремені" } },
            { "корінь", new[] { "кореня", "кореню", "корінь", "коренем", "корені" } },
            { "попіл", new[] { "попелу", "попелу", "попіл", "попелом", "попелі" } },
            { "лід", new[] { "льоду", "льоду", "лід", "льодом", "льоду" } },
            { "ріг", new[] { "рога", "рогу", "ріг", "рогом", "розі" } },
            { "рій", new[] { "рою", "рою", "рій", "роєм", "рої" } },
            { "дріт", new[] { "дроту", "дроту", "дріт", "дротом", "дроті" } },
            { "віск", new[] { "воску", "воску", "віск", "воском", "воску" } },
            { "сік", new[] { "соку", "соку", "сік", "соком", "соку" } },
            { "пісок", new[] { "піску", "піску", "пісок", "піском", "піску" } },
            { "мед", new[] { "меду", "меду", "мед", "медом", "меду" } },
            { "день", new[] { "дня", "дню", "день", "днем", "дні" } },
            { "рот", new[] { "рота", "ротові", "рот", "ротом", "роті" } },
            { "лев", new[] { "лева", "левові", "лева", "левом", "левові" } },
            { "ведмідь", new[] { "ведмедя", "ведмедеві", "ведмедя", "ведмедем", "ведмедеві" } },
            { "майстер", new[] { "майстра", "майстрові", "майстра", "майстром", "майстрові" } },
            { "вітер", new[] { "вітру", "вітру", "вітер", "вітром", "вітрі" } },
            { "урок", new[] { "уроку", "уроку", "урок", "уроком", "уроці" } },
            { "шати", new[] { "шат", "шатам", "шати", "шатами", "шатах" } },
            { "потік", new[] { "потоку", "потоку", "потік", "потоком", "потоці" } },
            { "стіл", new[] { "стола", "столу", "стіл", "столом", "столі" } },
            { "міст", new[] { "мосту", "мосту", "міст", "мостом", "мосту" } },
            { "поміст", new[] { "помосту", "помосту", "поміст", "помостом", "помості" } },
            { "хвіст", new[] { "хвоста", "хвостові", "хвіст", "хвостом", "хвості" } },
            { "наріст", new[] { "наросту", "наросту", "наріст", "наростом", "нарості" } },
            { "пиріг", new[] { "пирога", "пирогу", "пиріг", "пирогом", "пирозі" } },
            { "батіг", new[] { "батога", "батогу", "батіг", "батогом", "батозі" } },
            { "плід", new[] { "плоду", "плоду", "плід", "плодом", "плоді" } },
            { "привід", new[] { "приводу", "приводу", "привід", "приводом", "приводі" } },
            { "самохід", new[] { "самохода", "самоходу", "самохід", "самоходом", "самоході" } },
            { "дзвін", new[] { "дзвона", "дзвону", "дзвін", "дзвоном", "дзвоні" } },
            { "набір", new[] { "набору", "набору", "набір", "набором", "наборі" } },
            { "отвір", new[] { "отвору", "отвору", "отвір", "отвором", "отворі" } },
            { "зір", new[] { "зору", "зору", "зір", "зором", "зорі" } },
            { "якір", new[] { "якоря", "якорю", "якір", "якорем", "якорі" } },
            { "тхір", new[] { "тхора", "тхорові", "тхора", "тхором", "тхорові" } },
            { "пес", new[] { "пса", "псові", "пса", "псом", "псові" } },
            { "ніс", new[] { "носа", "носу", "ніс", "носом", "носі" } },
            { "сніп", new[] { "снопа", "снопу", "сніп", "снопом", "снопі" } },
            { "тупіт", new[] { "тупоту", "тупоту", "тупіт", "тупотом", "тупоті" } },
            { "папір", new[] { "паперу", "паперу", "папір", "папером", "папері" } },
            { "рівень", new[] { "рівня", "рівню", "рівень", "рівнем", "рівні" } },
            { "блазень", new[] { "блазня", "блазневі", "блазня", "блазнем", "блазневі" } },
            { "пристрій", new[] { "пристрою", "пристрою", "пристрій", "пристроєм", "пристрої" } },
            { "сувій", new[] { "сувою", "сувою", "сувій", "сувоєм", "сувої" } },
            { "ніщо", new[] { "нічого", "нічому", "ніщо", "нічим", "нічому" } },
            // feminine on a consonant (кість → кості, кістю)
            { "кість", new[] { "кості", "кості", "кість", "кістю", "кості" } },
            { "сіль", new[] { "солі", "солі", "сіль", "сіллю", "солі" } },
            { "ніч", new[] { "ночі", "ночі", "ніч", "ніччю", "ночі" } },
            { "піч", new[] { "печі", "печі", "піч", "піччю", "печі" } },
            { "річ", new[] { "речі", "речі", "річ", "річчю", "речі" } },
            { "кров", new[] { "крові", "крові", "кров", "кров’ю", "крові" } },
            { "мати", new[] { "матері", "матері", "матір", "матір’ю", "матері" } },
            // plural with an irregular genitive
            { "двері", new[] { "дверей", "дверям", "двері", "дверима", "дверях" } },
            { "люди", new[] { "людей", "людям", "людей", "людьми", "людях" } },
            { "діти", new[] { "дітей", "дітям", "дітей", "дітьми", "дітях" } },
            { "очі", new[] { "очей", "очам", "очі", "очима", "очах" } },
            { "плечі", new[] { "плечей", "плечам", "плечі", "плечима", "плечах" } },
            { "гроші", new[] { "грошей", "грошам", "гроші", "грошима", "грошах" } },
            { "чоботи", new[] { "чобіт", "чоботам", "чоботи", "чоботами", "чоботах" } },
            { "бджоли", new[] { "бджіл", "бджолам", "бджіл", "бджолами", "бджолах" } },
            { "ворота", new[] { "воріт", "воротам", "ворота", "воротами", "воротах" } },
            { "гори", new[] { "гір", "горам", "гори", "горами", "горах" } },
            { "нори", new[] { "нір", "норам", "нори", "норами", "норах" } },
            { "ноги", new[] { "ніг", "ногам", "ноги", "ногами", "ногах" } },
            { "кози", new[] { "кіз", "козам", "кіз", "козами", "козах" } },
            { "сльози", new[] { "сліз", "сльозам", "сльози", "сльозами", "сльозах" } },
        };

        // inanimate masculine nouns with the genitive on -у, -ю: substances, places, happenings (газу, лісу, викиду)
        static readonly HashSet<string> GenitiveU = new HashSet<string>
        {
            "газ", "дим", "хром", "пил", "мох", "гіпс", "рис", "шовк", "мармур", "базальт", "граніт", "кварцит", "пісковик",
            "вапняк", "сланець", "мергель", "крохмаль", "лігнін", "бетон", "фунгіцид", "дефоліант", "гумоклей", "клей",
            "ооліт", "моноліт", "серпентиніт", "сталагміт", "магніт", "смарагд", "сапфір", "топаз", "агат", "аметист",
            "перидот", "корал", "космос", "туман", "терен", "вакуум", "форум", "храм", "ліс", "світ", "цвіт", "корпус",
            "ярус", "імпульс", "рельєф", "риф", "погляд", "заряд", "викид", "зсув", "подих", "нюх", "сплеск", "спалах",
            "злочин", "масив", "трактат", "намет", "порт", "паркан", "трон", "приціл", "відсік", "лабіринтит", "причал",
            "гай", "край", "сир", "вир", "шар", "базар", "бар’єр", "тераріум", "укус", "кабель", "брухт", "метал", "жир",
            "ґрунт", "торф", "бруд", "шум", "звук", "чай", "обладунок", "мул", "азот", "кисень", "графен", "пісок",
        };

        // the ends of compound nouns of that kind: «самоцвіт», «пінобетон», «механізм»
        static readonly string[] GenitiveUEnds = { "цвіт", "бетон", "ізм", "изм", "ярус" };

        static bool TakesU(string lower)
        {
            if (GenitiveU.Contains(lower) || lower.EndsWith("арій") || lower.EndsWith("орій")) return true;
            foreach (string end in GenitiveUEnds)
                if (lower.EndsWith(end) && lower.Length > end.Length) return true;
            return false;
        }

        // -ар, -яр, -ир that decline soft (ліхтаря, упиря): people on -ар, -яр but these few, and the things listed
        static readonly HashSet<string> HardPeople = new HashSet<string> { "долар", "комар", "гусар", "яничар" };
        static readonly HashSet<string> SoftThings = new HashSet<string>
        {
            "ліхтар", "вівтар", "календар", "інвентар", "буквар", "упир", "пластир", "богатир",
        };

        static bool SoftR(string lower, bool animate)
        {
            if (lower.EndsWith("ар") || lower.EndsWith("яр")) return animate ? !HardPeople.Contains(lower) : SoftThings.Contains(lower);
            if (lower.EndsWith("ир")) return SoftThings.Contains(lower);
            return false;
        }

        static readonly HashSet<string> NoFleeting = new HashSet<string> { "пророк", "порок" };

        // мішок → мішка, огірок → огірка, виповзок → виповзка: -ок after a consonant; not after л, р that follow
        // another consonant (блок, інтерлок, строк), nor пророк
        static bool FleetingO(string lower)
        {
            if (!lower.EndsWith("ок") || lower.Length < 5 || NoFleeting.Contains(lower)) return false;
            char before = lower[lower.Length - 3], further = lower[lower.Length - 4];
            if ("аоеиіуюяєї".IndexOf(before) >= 0) return false;   // скорпіок
            return !("лр".IndexOf(before) >= 0 && "аоеиіуюяєї".IndexOf(further) < 0);
        }

        /// <summary>A noun in the nominative of gender, in case c.</summary>
        public static string Noun(string word, UkGender gender, bool animate, UkCase c)
        {
            string lower = word.ToLowerInvariant();
            if (Irregular.TryGetValue(lower, out string[] forms))
            {
                string form = forms[(int)c - 1];
                if (c == UkCase.Accusative && animate && (gender == UkGender.Masculine || gender == UkGender.Plural))
                    form = forms[0];
                return MatchCase(word, form);
            }
            char last = lower[lower.Length - 1];
            if (gender == UkGender.Plural) return Plural(word, lower, animate, c);
            if (gender == UkGender.Neuter && animate && Young(lower)) return YoungOne(word, c);   // троленя → троленяти
            if (last == 'а' || last == 'я')
            {
                if (gender == UkGender.Neuter && last == 'я') return NeuterYa(word, lower, c);   // знання, вугілля
                return FirstDeclension(word, lower, c);                                         // граната, броня, Дойоба
            }
            // a foreign woman's name on a consonant never changes (Меєгінд)
            if (gender == UkGender.Feminine && char.IsUpper(word[0]) && last != 'ь') return word;
            if (gender == UkGender.Feminine) return ThirdDeclension(word, lower, c);  // сталь, мідь, плоть
            if (last == 'о' || last == 'е' || last == 'є') return NeuterO(word, lower, c);
            return SecondDeclension(word, lower, animate, c);
        }

        static string MatchCase(string word, string form) =>
            char.IsUpper(word[0]) ? char.ToUpperInvariant(form[0]) + form.Substring(1) : form;

        // the consonant before a dative or locative -і: г → з, к → ц, х → с (рука → руці)
        static string Soften(string stem)
        {
            if (stem.EndsWith("г")) return stem.Substring(0, stem.Length - 1) + "з";
            if (stem.EndsWith("к")) return stem.Substring(0, stem.Length - 1) + "ц";
            if (stem.EndsWith("х")) return stem.Substring(0, stem.Length - 1) + "с";
            return stem;
        }

        static bool Sibilant(string stem) => stem.EndsWith("ж") || stem.EndsWith("ч") || stem.EndsWith("ш") || stem.EndsWith("щ");

        static bool VowelBefore(string lower) =>
            lower.Length > 1 && "аоеиіуюяєї’'ʼ".IndexOf(lower[lower.Length - 2]) >= 0;

        static string FirstDeclension(string word, string lower, UkCase c)
        {
            string stem = word.Substring(0, word.Length - 1);
            string lowStem = lower.Substring(0, lower.Length - 1);
            if (lower.EndsWith("я"))
            {
                if (VowelBefore(lower))   // змія, мрія, сім’я
                    return stem + Pick(c, "ї", "ї", "ю", "єю", "ї");
                return stem + Pick(c, "і", "і", "ю", "ею", "і");
            }
            if (Sibilant(lowStem))         // каша, межа
                return stem + Pick(c, "і", "і", "у", "ею", "і");
            string soft = MatchStem(stem, Soften(lowStem));
            switch (c)
            {
                case UkCase.Genitive: return stem + "и";
                case UkCase.Dative: return soft + "і";
                case UkCase.Accusative: return stem + "у";
                case UkCase.Instrumental: return stem + "ою";
                default: return soft + "і";
            }
        }

        // the stem with its last letter as changed in lowered, its capitals kept
        static string MatchStem(string stem, string lowered) =>
            lowered.Length == stem.Length && !lowered.Equals(stem, StringComparison.OrdinalIgnoreCase)
                ? stem.Substring(0, stem.Length - 1) + lowered[lowered.Length - 1]
                : stem;

        // a young creature: кошеня, троленя, курча (not знання: a verbal noun doubles its н)
        static bool Young(string lower) =>
            lower.EndsWith("еня") && !lower.EndsWith("ення") || lower.EndsWith("ча") || lower.EndsWith("жа") || lower.EndsWith("ша");

        static string YoungOne(string word, UkCase c) => c == UkCase.Accusative ? word : word + Pick(c, "ти", "ті", null, "м", "ті");

        static string NeuterYa(string word, string lower, UkCase c)
        {
            string stem = word.Substring(0, word.Length - 1);
            return c == UkCase.Accusative ? word : stem + Pick(c, "я", "ю", null, "ям", "і");
        }

        static string NeuterO(string word, string lower, UkCase c)
        {
            if (c == UkCase.Accusative) return word;
            string stem = word.Substring(0, word.Length - 1);
            string lowStem = lower.Substring(0, lower.Length - 1);
            if (lower.EndsWith("о"))
                return c == UkCase.Locative ? MatchStem(stem, Soften(lowStem)) + "і" : stem + Pick(c, "а", "у", null, "ом", null);
            if (lower.EndsWith("є")) return stem + Pick(c, "я", "ю", null, "єм", "ї");
            if (Sibilant(lowStem)) return stem + Pick(c, "а", "у", null, "ем", "і");   // плече
            return stem + Pick(c, "я", "ю", null, "ем", "і");                             // серце, поле
        }

        static string ThirdDeclension(string word, string lower, UkCase c)
        {
            if (c == UkCase.Accusative) return word;
            string stem = lower.EndsWith("ь") ? word.Substring(0, word.Length - 1) : word;
            // the suffix -ість opens to -ості: радість → радості (but радістю; повість → повісті)
            if (c != UkCase.Instrumental && lower.EndsWith("ість") && !lower.EndsWith("вість")) return word.Substring(0, word.Length - 4) + "ості";
            if (c != UkCase.Instrumental) return stem + "і";
            // the instrumental doubles a consonant after a vowel (тінню, міддю), keeps it after a consonant (радістю)
            string lowStem = stem.ToLowerInvariant();
            char consonant = lowStem[lowStem.Length - 1];
            bool afterVowel = lowStem.Length > 1 && "аоеиіуюяєї".IndexOf(lowStem[lowStem.Length - 2]) >= 0;
            if ("бпвмф".IndexOf(consonant) >= 0) return stem + "’ю";
            return afterVowel ? stem + consonant + "ю" : stem + "ю";
        }

        static string SecondDeclension(string word, string lower, bool animate, UkCase c)
        {
            if (c == UkCase.Accusative && !animate) return word;
            if (c == UkCase.Accusative) c = UkCase.Genitive;
            string stem = word, lowStem = lower;
            bool common = !char.IsUpper(word[0]);
            bool u = !animate && TakesU(lower);   // газу, лісу; клею, мергелю
            string soft = u ? "ю" : "я";
            // a vowel that drops before the ending: мішок → мішка
            if (common && FleetingO(lower)) { stem = word.Substring(0, word.Length - 2) + word[word.Length - 1]; lowStem = stem.ToLowerInvariant(); }
            if (common && lower.EndsWith("інь") && lower.Length > 4)   // струмінь → струменя, гребінь → гребеня
            {
                stem = word.Substring(0, word.Length - 3) + "ен";
                return stem + Pick(c, soft, animate ? "еві" : "ю", null, "ем", animate ? "еві" : "і");
            }
            if (common && lower.EndsWith("оть") && lower.Length > 4)   // кіготь → кігтя, лікоть → ліктя
            {
                stem = word.Substring(0, word.Length - 3) + "т";
                return stem + Pick(c, soft, animate ? "еві" : "ю", null, "ем", animate ? "еві" : "і");
            }
            if (lower.EndsWith("ець") && lower.Length > 4)   // гаманець → гаманця, сланець → сланцю, стрілець → стрільця
            {
                stem = word.Substring(0, word.Length - 3) + (lower.EndsWith("лець") ? "ьц" : "ц");
                return stem + Pick(c, soft, animate ? "еві" : "ю", null, "ем", animate ? "еві" : "і");
            }
            if (lower.EndsWith("ь"))
            {
                stem = word.Substring(0, word.Length - 1);
                return stem + Pick(c, soft, animate ? "еві" : "ю", null, "ем", animate ? "еві" : "і");
            }
            if (lower.EndsWith("й"))
            {
                stem = word.Substring(0, word.Length - 1);
                return stem + Pick(c, soft, animate ? "єві" : "ю", null, "єм", animate ? "єві" : "ї");
            }
            if (SoftR(lower, animate))   // лікар, ліхтар, упир: soft
                return stem + Pick(c, soft, animate ? "еві" : "ю", null, "ем", animate ? "еві" : "і");
            if (Sibilant(lowStem))     // меч, ніж
                return stem + Pick(c, u ? "у" : "а", animate ? "еві" : "у", null, "ем", animate ? "еві" : "і");
            string loc = animate ? "ові" : lowStem.EndsWith("к") || lowStem.EndsWith("г") || lowStem.EndsWith("х") ? "у" : "і";
            return stem + Pick(c, u ? "у" : "а", animate ? "ові" : "у", null, "ом", loc);
        }

        const string Vowels = "аоеиіуюяєї’'ʼ";

        // a stem on two consonants, the last л, р or н, takes a vowel between them where the ending is gone: о after к,
        // г, х (ікла → ікол, вікна → вікон), е elsewhere (весла → весел, сосни → сосен, зябра → зябер); not муфт, бритв
        static string Cluster(string stem)
        {
            string low = stem.ToLowerInvariant();
            if (low.Length < 2 || "лрн".IndexOf(low[low.Length - 1]) < 0 || (Vowels + "ь").IndexOf(low[low.Length - 2]) >= 0) return stem;
            string vowel = "кгх".IndexOf(low[low.Length - 2]) >= 0 ? "о" : "е";
            return stem.Substring(0, stem.Length - 1) + vowel + stem[stem.Length - 1];
        }

        // the soft genitive plural: пісні → пісень, копальні → копалень, кухні → кухонь, броні → бронь
        static string SoftCluster(string stem)
        {
            string s = stem;
            if (s.Length > 2 && char.ToLowerInvariant(s[s.Length - 2]) == 'ь') s = s.Remove(s.Length - 2, 1);
            return Cluster(s) + "ь";
        }

        // a doubled consonant before the last letter (сухожилля, знання)
        static bool Doubled(string lower) =>
            lower.Length > 3 && lower[lower.Length - 2] == lower[lower.Length - 3] && "аоеиіуюяєї".IndexOf(lower[lower.Length - 2]) < 0;

        static string Plural(string word, string lower, bool animate, UkCase c)
        {
            string stem = word.Substring(0, word.Length - 1);
            char last = lower[lower.Length - 1];
            bool soft = last == 'і' || last == 'ї' || last == 'я';
            string gen = PluralGenitive(word, lower, stem, last);
            switch (c)
            {
                case UkCase.Genitive: return gen;
                case UkCase.Accusative: return animate ? gen : word;
                case UkCase.Dative: return stem + (soft ? "ям" : "ам");
                case UkCase.Instrumental: return stem + (soft ? "ями" : "ами");
                default: return stem + (soft ? "ях" : "ах");
            }
        }

        // the genitive plural, by the singular: a feminine (труби, the translation having «трубою») ends bare, a
        // masculine takes -ів (гриби → грибів)
        static string PluralGenitive(string word, string lower, string stem, char last)
        {
            string lowStem = lower.Substring(0, lower.Length - 1);
            if ((last == 'и' || last == 'і') && AdjectiveLexicon.IsMasculinePluralStem(lowStem)) return stem + "ів";   // залишків
            if (lower.EndsWith("ки"))
            {
                // гаки, ролики, диски, уламки: masculine; рукавички, голки: feminine
                string beforeK = lower.Substring(0, lower.Length - 2);
                bool masculine = Vowels.IndexOf(lower[lower.Length - 3]) >= 0
                                 || AdjectiveLexicon.IsNoun(lowStem) || AdjectiveLexicon.IsNoun(beforeK + "ок");
                if (masculine && !AdjectiveLexicon.IsFeminineStem(lowStem)) return stem + "ів";
                return word.Substring(0, word.Length - 2) + "ок";                                 // рукавички → рукавичок
            }
            if (lower.EndsWith("сті")) return stem + "ей";                                        // цінностей, кистей, гостей
            if (lower.EndsWith("иці")) return stem + "ь";                                         // ножиці → ножиць
            if (last == 'а') return Cluster(stem);                                                   // жвал, ікол, зябер
            if (lower.EndsWith("ця")) return word.Substring(0, word.Length - 2) + "ець";           // кільця → кілець
            if (lower.EndsWith("ття")) return stem + "ів";                                         // почуття → почуттів
            if (last == 'я' && Doubled(lower)) return word.Substring(0, word.Length - 2) + "ь";    // сухожиль, знань
            if (last == 'я') return stem + "ів";                                                     // поля → полів
            if (lower.EndsWith("ії")) return stem + "й";                                           // модифікації → модифікацій
            if (last == 'ї') return stem + "їв";                                                     // краї → країв
            if (last == 'и' && AdjectiveLexicon.IsFeminineStem(lowStem) && !AdjectiveLexicon.IsNoun(lowStem)) return Cluster(stem);   // труб, сосен
            if (last == 'і' && AdjectiveLexicon.IsThirdDeclensionStem(lowStem)) return stem + "ей";   // тіней, кистей
            if (last == 'і' && AdjectiveLexicon.IsSoftFeminineStem(lowStem))                       // пісень, каш
                return Sibilant(lowStem) ? stem : SoftCluster(stem);
            return stem + "ів";                                                                      // окуляри → окулярів
        }
    }
}
