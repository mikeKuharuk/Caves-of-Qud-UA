using HarmonyLib;
using Qud.API;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The player's accomplishments the game's C# writes in English: the journal's line («You journeyed to
    /// Golgotha.»), the mural in the player's tomb and the gospel the villages tell at the end (=name= is the player).
    /// JournalAPI.AddAccomplishment keeps what it is given, so the Journal table gives it first
    /// (codescan.scan_journal). The mural's and the gospel's HistorySpice (&lt;spice…&gt;, =name=, =year=) stays for
    /// AddAccomplishment to expand, in Ukrainian; what the string tables gave passes.
    /// </summary>
    [HarmonyPatch(typeof(JournalAPI), nameof(JournalAPI.AddAccomplishment))]
    static class AccomplishmentPatch
    {
        static void Prefix(ref string text, ref string muralText, ref string gospelText)
        {
            if (!Uk.Active) return;
            text = CodeText.Translate("Journal", text);
            muralText = CodeText.Translate("Journal", muralText);
            gospelText = CodeText.Translate("Journal", gospelText);
        }
    }
}
