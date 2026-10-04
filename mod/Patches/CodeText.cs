using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
using CavesOfQudUA.Grammar;
using XRL.Blueprints;
using XRL.World;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The English the game's C# writes, in Ukrainian, from the code tables (CodeTables: the Code.* catalogs). A
    /// key is the text exactly as the game produces it, or a pattern where {0}, {1}… match what the code computes
    /// («-{0} DV» → «-{0} ЗУ»); a translation counts with a number hole by {n:хід:ходи:ходів} («через {0}
    /// {0:хід:ходи:ходів}»). A text with several lines is looked up line by line. Agreement: a key listed in the
    /// table's ".agree" companion is a masculine adjective phrase that agrees with the object it describes.
    /// What is not found stays English and is written once to Player.log as «[uk-miss] table: text», so play can
    /// grow the tables (tools/misses.py).
    /// </summary>
    public static class CodeText
    {
        sealed class Table
        {
            public readonly Dictionary<string, string> Exact = new Dictionary<string, string>();
            public readonly List<(Regex Match, string Key, string Text)> Patterns = new List<(Regex, string, string)>();
        }

        static readonly Dictionary<string, Table> Tables = new Dictionary<string, Table>();
        static readonly HashSet<string> Missed = new HashSet<string>();
        static readonly Dictionary<string, string> Memo = new Dictionary<string, string>();
        static readonly Regex Hole = new Regex(@"\{(\d+)\}");
        static readonly Regex Counted = new Regex(@"\{(\d+):([^{}]*)\}");
        static readonly Regex English = new Regex("[A-Za-z]{2}");
        static readonly Regex EnglishWord = new Regex("[A-Za-z]{3}");
        // a key's name in a button («[{{keybind|Esc}}] Скасувати»), and a variable the game has not replaced yet
        // («Кидок проти кровотечі: =statistics[Toughness].title=»): English letters, but nothing to translate
        static readonly Regex Keybind = new Regex(@"\{\{keybind\|[^{}]*\}\}");
        static readonly Regex GameVariable = new Regex(@"=[A-Za-z_][\w.\[\]]*(?:[:|#][^=\n]*)?=");

        /// <summary>What the player reads of text: its markup, key names and unreplaced variables aside.</summary>
        static string Readable(string text)
        {
            return UkrainianForms.StripMarkup(GameVariable.Replace(Keybind.Replace(text, " "), " "));
        }

        /// <summary>Whether text, its markup aside, has English in it: what the string tables did not translate.</summary>
        public static bool HasEnglish(string text)
        {
            return !string.IsNullOrEmpty(text) && English.IsMatch(Readable(text));
        }

        static readonly Regex Variable = new Regex(@"=[A-Za-z_][\w.]*(?::[^=\n]*)?=");

        /// <summary>
        /// Whether a translation still has an English word in it, its markup and our grammar variables aside
        /// (=object.p:…=): a general key that took a hole it should not have.
        /// </summary>
        public static bool HasEnglishWord(string text)
        {
            return !string.IsNullOrEmpty(text) && EnglishWord.IsMatch(Variable.Replace(UkrainianForms.StripMarkup(text), " "));
        }

        /// <summary>
        /// The Ukrainian for text from table, agreed with agreeWith where the table says so. A text with no English in
        /// it (the string tables already translated it) passes at once; results are remembered, since the HUD asks for
        /// the same effect descriptions every frame.
        /// </summary>
        public static string Translate(string table, string text, GameObject agreeWith = null)
        {
            if (!HasEnglish(text)) return text;
            string memoKey = table + "\u0001" + (agreeWith == null ? "" : ((int)UkrainianGender.Of(agreeWith)).ToString())
                             + "\u0001" + text;
            if (Memo.TryGetValue(memoKey, out string cached)) return cached;
            string result = Compute(table, text, agreeWith);
            if (Memo.Count > 20000) Memo.Clear();
            Memo[memoKey] = result;
            return result;
        }

        static string Compute(string table, string text, GameObject agreeWith)
        {
            Table t = Load(table);
            string whole = Find(table, t, text, agreeWith);
            if (whole != null) return whole;
            if (text.IndexOf('\n') < 0)
            {
                Miss(table, text);
                return text;
            }
            string[] lines = text.Split('\n');
            bool any = false;
            for (int i = 0; i < lines.Length; i++)
            {
                // a «\r\n» line is looked up without its «\r» (the keys have none) and keeps it
                bool cr = lines[i].EndsWith("\r");
                string plain = cr ? lines[i].Substring(0, lines[i].Length - 1) : lines[i];
                // a line the string tables gave (a template's Ukrainian, above the English the code adds) passes
                if (!HasEnglish(plain)) continue;
                string line = Find(table, t, plain, agreeWith);
                if (line != null)
                {
                    lines[i] = cr ? line + "\r" : line;
                    any = true;
                }
                else Miss(table, plain);
            }
            return any ? string.Join("\n", lines) : text;
        }

        /// <summary>
        /// The entry for key, exact or by pattern ({n} filled in), or null (logged as a miss). For tables whose key
        /// is not the game's text itself, such as the DidX narration.
        /// </summary>
        public static string Lookup(string table, string key)
        {
            string found = Peek(table, key);
            if (found == null && !string.IsNullOrEmpty(key)) Miss(table, key);
            return found;
        }

        /// <summary>Lookup without the miss: for a caller that has another key to try (DidX's «*» templates).</summary>
        public static string Peek(string table, string key)
        {
            return string.IsNullOrEmpty(key) ? null : Find(table, Load(table), key, null);
        }

        static string Find(string name, Table t, string text, GameObject agreeWith)
        {
            if (t.Exact.TryGetValue(text, out string exact)) return Agree(name, text, exact, agreeWith);
            foreach (var p in t.Patterns)
            {
                Match m = p.Match.Match(text);
                if (!m.Success) continue;
                string result = Counted.Replace(p.Text, h =>
                {
                    Group g = m.Groups["h" + h.Groups[1].Value];
                    return g.Success ? FormFor(g.Value, h.Groups[2].Value.Split(':')) : h.Value;
                });
                result = Hole.Replace(result, h =>
                {
                    Group g = m.Groups["h" + h.Groups[1].Value];
                    return g.Success ? HoleText(g.Value) : h.Value;
                });
                return Agree(name, p.Key, result, agreeWith);
            }
            return null;
        }

        /// <summary>
        /// What a hole holds, in Ukrainian when it is one of the words the code keeps in constants (the Words table:
        /// a journal tab, a stance, what a breath is made of): «{{W|Locations > Artifacts}}» → «{{W|Місця > …}}»; or a
        /// statistic's ID, which the code writes as it is («a difficulty 20 Toughness save»), by the string tables'
        /// title for it («Витривалість»).
        /// </summary>
        static string HoleText(string value)
        {
            return CodeTables.Get("Words", value) ?? StatTitle(value) ?? value;
        }

        /// <summary>
        /// The title the string tables give the statistic whose ID the value is («Toughness» → «Витривалість»), or
        /// null. tools/patch-tests puts its own here: outside the game no blueprints are loaded.
        /// </summary>
        public static System.Func<string, string> StatTitle = GameStatTitle;

        static string GameStatTitle(string value)
        {
            if (value.Length < 2 || value.Length > 24 || !char.IsUpper(value[0])) return null;
            foreach (char c in value)
                if (!char.IsLetter(c)) return null;
            try
            {
                return StatisticBlueprint.TryGet(value.AsSpan(), out StatisticBlueprint stat) ? stat.DisplayTitle : null;
            }
            catch (System.Exception)
            {
                return null;   // the blueprints are not loaded yet
            }
        }

        /// <summary>
        /// The form of {n:хід:ходи:ходів} for the number hole n holds: 1, 2–4, 5+. A number that is not whole takes
        /// the 2–4 form, the nearest to the genitive singular it needs («2,5 клітинки»).
        /// </summary>
        static string FormFor(string number, string[] forms)
        {
            string plain = UkrainianForms.StripMarkup(number).Trim();
            if (long.TryParse(plain, NumberStyles.Integer, CultureInfo.InvariantCulture, out long n))
                return UkrainianForms.ByNumber(n, forms);
            return forms[forms.Length > 1 ? 1 : 0];
        }

        static string Agree(string table, string key, string text, GameObject agreeWith)
        {
            if (agreeWith == null || CodeTables.Get(table + ".agree", key) == null) return text;
            return UkrainianForms.AgreeAdjective(text, UkrainianGender.Of(agreeWith), AdjectiveForms.Get, regular: true);
        }

        static Table Load(string name)
        {
            if (Tables.TryGetValue(name, out Table t)) return t;
            t = new Table();
            foreach (var pair in CodeTables.All(name))
            {
                if (Hole.IsMatch(pair.Key)) t.Patterns.Add((PatternOf(pair.Key), pair.Key, pair.Value));
                else t.Exact[pair.Key] = pair.Value;
            }
            // the most specific pattern first: the one with the most literal text
            t.Patterns.Sort((a, b) => Hole.Replace(b.Key, "").Length.CompareTo(Hole.Replace(a.Key, "").Length));
            Tables[name] = t;
            return t;
        }

        /// <summary>
        /// «-{0} DV» → ^-(anything but a line break, lazily) DV$. A hole never spans lines, so a pattern that starts or
        /// ends with one cannot swallow a multi-line text: that is matched line by line. Each hole is a group named
        /// after its number, so a translation's {n} is the key's {n} wherever it stands; a number the key repeats
        /// must match the same text again.
        /// </summary>
        public static Regex PatternOf(string key)
        {
            var sb = new StringBuilder("^");
            var seen = new HashSet<string>();
            int last = 0;
            foreach (Match m in Hole.Matches(key))
            {
                string n = m.Groups[1].Value;
                sb.Append(Regex.Escape(key.Substring(last, m.Index - last)));
                // a part may come out empty, but never spans lines
                sb.Append(seen.Add(n) ? "(?<h" + n + ">[^\n]*?)" : @"\k<h" + n + ">");
                last = m.Index + m.Length;
            }
            sb.Append(Regex.Escape(key.Substring(last))).Append('$');
            return new Regex(sb.ToString());
        }

        /// <summary>Logs text as missing from table (once): for a caller that found a key it cannot use.</summary>
        public static void LogMiss(string table, string text) => Miss(table, text);

        static void Miss(string table, string text)
        {
            if (!Uk.Active || string.IsNullOrEmpty(text) || !EnglishWord.IsMatch(Readable(text))) return;
            if (!Missed.Add(table + "\u0001" + text)) return;
            try { MetricsManager.LogInfo("[uk-miss] " + table + ": " + text); }
            catch (System.Exception) { }   // a log line must never break the text (and there is no Unity in the tests)
        }
    }
}
