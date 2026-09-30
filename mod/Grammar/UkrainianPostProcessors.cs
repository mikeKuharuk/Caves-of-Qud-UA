using XRL.World;
using XRL.World.Text.Attributes;
using XRL.World.Text.Delegates;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// English post-processors that would damage Ukrainian text, replaced while the game runs in Ukrainian. They
    /// still appear in templates the game builds in code and in HistorySpice fragments whose structure stays English:
    ///   |article, |Article        Grammar.A: "a "/"an " before the word → nothing (a capital if asked)
    ///   |pluralize, |plural       Grammar.Pluralize: English endings → the word unchanged
    ///   |title, |titleCaseWithArticle   Every Word Capitalized → only the first letter, as Ukrainian titles are
    ///   |a.to.an, |scanForAn      "a" → "an" → nothing to do
    /// </summary>
    [HasVariableReplacer(Lang = "uk")]
    public static class UkrainianPostProcessors
    {
        [VariablePostProcessor(new string[] { "article" }, Capitalization = true, Override = true)]
        public static void Article(VariableContext Context)
        {
            if (Context.Capitalize) CapitalizeValue(Context);
        }

        [VariablePostProcessor(new string[] { "pluralize", "plural" }, Override = true)]
        public static void Pluralize(VariableContext Context)
        {
        }

        [VariablePostProcessor(new string[] { "pluralize", "plural" }, Override = true)]
        public static void Pluralize(VariableContext Context, int Number)
        {
        }

        [VariablePostProcessor(new string[] { "pluralize", "plural" }, Override = true)]
        public static void Pluralize(VariableContext Context, GameObject Object)
        {
        }

        [VariablePostProcessor(new string[] { "title", "titleCaseWithArticle" }, Override = true)]
        public static void Title(VariableContext Context)
        {
            CapitalizeValue(Context);
        }

        [VariablePostProcessor(new string[] { "scanForAn", "a.to.an" }, Override = true)]
        public static void ScanForAn(VariableContext Context)
        {
        }

        static void CapitalizeValue(VariableContext Context)
        {
            string value = Context.Value.ToString();
            string capitalized = UkrainianForms.Capitalize(value);
            if (capitalized == value) return;
            Context.Value.Clear();
            Context.Value.Append(capitalized);
        }
    }
}
