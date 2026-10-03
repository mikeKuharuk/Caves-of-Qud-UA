using XRL.Language;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// Shared checks for the Harmony patches. The game applies every [HarmonyPatch] class of the mod on load
    /// (ModInfo.ApplyHarmonyPatches), whatever the language, so each patch must step aside unless the game runs in
    /// Ukrainian.
    /// </summary>
    public static class Uk
    {
        public static bool Active => ForceActive ?? LanguageLoader.ActiveLanguage == "uk";

        /// <summary>For tools/patch-tests, which run the patches outside the game (no options, no Unity).</summary>
        public static bool? ForceActive;

        /// <summary>
        /// Set by tools/patch-tests: there is no Unity, so patches on Unity components (PopupMessage) cannot be applied
        /// and step aside through their Prepare().
        /// </summary>
        public static bool OutsideUnity;

        /// <summary>Whether the text holds a Cyrillic letter: our words, as opposed to English the code wrote.</summary>
        public static bool HasCyrillic(string text)
        {
            if (string.IsNullOrEmpty(text)) return false;
            foreach (char c in text)
                if (c >= 'Ѐ' && c <= 'ӿ') return true;
            return false;
        }

        /// <summary>A Ukrainian word or phrase the game is about to treat with English morphology.</summary>
        public static bool Ours(string text) => Active && HasCyrillic(text);
    }
}
