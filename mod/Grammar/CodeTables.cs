using System.Collections.Generic;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// English text the game passes as it is (a species), with its Ukrainian translation: table → English →
    /// Ukrainian. `py tools/qud.py build` fills them into CodeTables.g.cs from the Code.* catalogs
    /// (tools/qudtr/codetables.py); without that file they stay empty and the English shows.
    /// </summary>
    public static partial class CodeTables
    {
        static readonly Dictionary<string, Dictionary<string, string>> Tables = new Dictionary<string, Dictionary<string, string>>();

        static CodeTables()
        {
            Fill(Tables);
        }

        static partial void Fill(Dictionary<string, Dictionary<string, string>> t);

        /// <summary>The Ukrainian for english in table, or null.</summary>
        public static string Get(string table, string english)
        {
            if (english == null || !Tables.TryGetValue(table, out Dictionary<string, string> entries)) return null;
            return entries.TryGetValue(english, out string text) ? text : null;
        }
    }
}
