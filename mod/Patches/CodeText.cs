using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using CavesOfQudUA.Grammar;
using XRL.World;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The English the game's C# writes, in Ukrainian, from the code tables (CodeTables: the Code.* catalogs). A
    /// key is the text exactly as the game produces it, or a pattern where {0}, {1}… match what the code computes
    /// («-{0} DV» → «-{0} ЗУ»). A text with several lines is looked up line by line. Agreement: a key listed in the
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
        static readonly Regex Hole = new Regex(@"\{(\d+)\}");

        /// <summary>The Ukrainian for text from table, agreed with agreeWith where the table says so.</summary>
        public static string Translate(string table, string text, GameObject agreeWith = null)
        {
            if (string.IsNullOrEmpty(text)) return text;
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
                string line = Find(table, t, lines[i], agreeWith);
                if (line != null)
                {
                    lines[i] = line;
                    any = true;
                }
                else Miss(table, lines[i]);
            }
            return any ? string.Join("\n", lines) : text;
        }

        static string Find(string name, Table t, string text, GameObject agreeWith)
        {
            if (t.Exact.TryGetValue(text, out string exact)) return Agree(name, text, exact, agreeWith);
            foreach (var p in t.Patterns)
            {
                Match m = p.Match.Match(text);
                if (!m.Success) continue;
                string result = Hole.Replace(p.Text, h =>
                {
                    int g = int.Parse(h.Groups[1].Value) + 1;
                    return g < m.Groups.Count ? m.Groups[g].Value : h.Value;
                });
                return Agree(name, p.Key, result, agreeWith);
            }
            return null;
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

        /// <summary>«-{0} DV» → ^-(.+?) DV$.</summary>
        public static Regex PatternOf(string key)
        {
            var sb = new StringBuilder("^");
            int last = 0;
            foreach (Match m in Hole.Matches(key))
            {
                sb.Append(Regex.Escape(key.Substring(last, m.Index - last))).Append("(.+?)");
                last = m.Index + m.Length;
            }
            sb.Append(Regex.Escape(key.Substring(last))).Append('$');
            return new Regex(sb.ToString(), RegexOptions.Singleline);
        }

        static void Miss(string table, string text)
        {
            if (!Uk.Active || string.IsNullOrEmpty(text) || !Regex.IsMatch(text, "[A-Za-z]{2}")) return;
            if (!Missed.Add(table + "\u0001" + text)) return;
            try { MetricsManager.LogInfo("[uk-miss] " + table + ": " + text); }
            catch (System.Exception) { }   // a log line must never break the text (and there is no Unity in the tests)
        }
    }
}
