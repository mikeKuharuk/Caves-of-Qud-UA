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
    /// and adds the mod's own: |uk.word (an English word from the code in Ukrainian), |uk.agree#X (an adjective
    /// agreed with X's gender) and |uk.f, |uk.n, |uk.pl (an adjective in a fixed gender).
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

        /// <summary>=rank|uk.word=: an English word from the code in Ukrainian (CodeWords).</summary>
        [VariablePostProcessor(new string[] { "uk.word" })]
        public static void Word(VariableContext Context)
        {
            string value = Context.Value.ToString();
            SetValue(Context, value, CodeWords.Translate(value));
        }

        /// <summary>
        /// =stat_title|uk.stat=: a statistic's ID the code passes as it is («Agility», in a skill's requirements) as
        /// the string tables title it («Спритність»). The short name small screens get is Ukrainian already and passes.
        /// </summary>
        [VariablePostProcessor(new string[] { "uk.stat" })]
        public static void Stat(VariableContext Context)
        {
            string value = Context.Value.ToString();
            SetValue(Context, value, Patches.CodeText.StatTitle(value) ?? value);
        }

        /// <summary>
        /// =modifier|uk.agree#subject=: a masculine adjective (or «X і Y») agreed with an object, by the uk-forms table
        /// and else by the regular endings: «Злий» → «Зла» for a female twin.
        /// </summary>
        [VariablePostProcessor(new string[] { "uk.agree" })]
        public static void Agree(VariableContext Context, GameObject Object)
        {
            if (Object != null) Agree(Context, UkrainianGender.Of(Object));
        }

        /// <summary>
        /// =x|uk.agree#rank=: the same with a noun given as text: a word from the code (CodeWords, a hunter's rank), or a
        /// translated noun with a qud-gender note (a liquid's name: «кривава солонувата вода»).
        /// </summary>
        [VariablePostProcessor(new string[] { "uk.agree" })]
        public static void Agree(VariableContext Context, string Word)
        {
            UkGender? gender = CodeWords.GenderOf(Word) ?? NounGenders.OfWord(Word);
            if (gender.HasValue) Agree(Context, gender.Value);
        }

        /// <summary>
        /// =verb|uk.v#subject=: a verb the code takes from the game's data (a device's «beep», a projectile's «whiz»: the
        /// Verbs code table, «пищить:пищите:пищать») in the form for that object: the player «ви», a plural «вони»,
        /// anyone else «він/вона». A verb the table does not know stays as it is.
        /// </summary>
        [VariablePostProcessor(new string[] { "uk.v" })]
        public static void Verb(VariableContext Context, GameObject Object)
        {
            string value = Context.Value.ToString();
            string forms = CodeTables.Get("Verbs", value);
            if (forms == null || Object == null) return;
            bool player = UkrainianGender.IsSecondPerson(Object);
            bool plural = !player && UkrainianGender.Of(Object) == UkGender.Plural;
            SetValue(Context, value, UkrainianForms.ByPerson(player, plural, forms.Split(':')));
        }

        /// <summary>
        /// =adj|uk.f=, =adj|uk.n=, =adj|uk.pl=: a masculine adjective in the feminine, neuter or plural, for a noun the
        /// template itself fixes («тверді й =…adjectives.!random|uk.pl= рештки»).
        /// </summary>
        [VariablePostProcessor(new string[] { "uk.f" })]
        public static void Feminine(VariableContext Context)
        {
            Agree(Context, UkGender.Feminine);
        }

        [VariablePostProcessor(new string[] { "uk.n" })]
        public static void Neuter(VariableContext Context)
        {
            Agree(Context, UkGender.Neuter);
        }

        [VariablePostProcessor(new string[] { "uk.pl" })]
        public static void Plural(VariableContext Context)
        {
            Agree(Context, UkGender.Plural);
        }

        static void Agree(VariableContext Context, UkGender gender)
        {
            string value = Context.Value.ToString();
            SetValue(Context, value, UkrainianForms.AgreeAdjective(value, gender, AdjectiveForms.Get, regular: true));
        }

        static void SetValue(VariableContext Context, string old, string value)
        {
            if (value == old) return;
            Context.Value.Clear();
            Context.Value.Append(value);
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
