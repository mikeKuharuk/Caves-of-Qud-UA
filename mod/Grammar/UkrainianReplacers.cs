using XRL.World;
using XRL.World.Text;
using XRL.World.Text.Attributes;
using XRL.World.Text.Delegates;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// Variables for Ukrainian translations (docs/grammar.md). They exist only while the game runs in Ukrainian.
    /// The forms are written in the translation itself, and the variable picks one:
    ///   =subject.v:б’є:б’єте:б’ють=              person and number (the player is «ви»)
    ///   =subject.g:упав:упала:упало:упали=      gender (the player takes the plural)
    ///   =object.g:його:її:його:їх:вас=          a fifth form, if given, is the player's own
    ///   =turns.plural:хід:ходи:ходів=            a number's word form (1 / 2–4 / 5+)
    ///   =object.n:acc=                          the name in a case (nom, gen, dat, acc, ins, loc)
    /// A capital first letter (=subject.V:…=, =subject.G:…=, =object.N:acc=) capitalizes the chosen form.
    /// v and g take a game object or a noun the game passes with its pronouns (GenderedNoun).
    /// </summary>
    [HasVariableReplacer(Lang = "uk")]
    public static class UkrainianReplacers
    {
        [VariableReplacer("v", Capitalization = true, Default = "")]
        public static string Verb(VariableContext Context, GameObject Object)
        {
            bool player = UkrainianGender.IsSecondPerson(Object);
            bool plural = !player && UkrainianGender.Of(Object) == UkGender.Plural;
            return Finish(Context, UkrainianForms.ByPerson(player, plural, Forms(Context)));
        }

        [VariableReplacer("v", Capitalization = true, Default = "")]
        public static string Verb(VariableContext Context, GenderedNoun Noun)
        {
            return Finish(Context, UkrainianForms.ByPerson(false, UkrainianGender.Of(Noun) == UkGender.Plural, Forms(Context)));
        }

        [VariableReplacer("g", Capitalization = true, Default = "")]
        public static string Gendered(VariableContext Context, GameObject Object)
        {
            bool player = UkrainianGender.IsSecondPerson(Object);
            return Finish(Context, UkrainianForms.ByGenderOrPlayer(player, UkrainianGender.Of(Object), Forms(Context)));
        }

        [VariableReplacer("g", Capitalization = true, Default = "")]
        public static string Gendered(VariableContext Context, GenderedNoun Noun)
        {
            return Finish(Context, UkrainianForms.ByGender(UkrainianGender.Of(Noun), Forms(Context)));
        }

        /// <summary>
        /// =object.p:«for the player»:«for anyone else»= — a phrase that names X in the third person, which «ви»
        /// cannot fill («розтрощує розум (ви)»). The player gets their own wording; anyone else the second form,
        /// where @ stands for the name as =object.name= prints it: =object.p:ваш розум:розум (@)=.
        /// </summary>
        [VariableReplacer("p", Capitalization = true, Default = "")]
        public static string Player(VariableContext Context, GameObject Object)
        {
            string[] forms = Forms(Context);
            string form = UkrainianForms.ForPlayerOrOther(UkrainianGender.IsSecondPerson(Object), forms);
            if (form.IndexOf('@') >= 0)
                form = form.Replace("@", Object.GetDisplayName(int.MaxValue, null, null, AsIfKnown: false, Single: false,
                    NoConfusion: false, NoColor: false, Stripped: false, ColorOnly: false, Visible: true, WithoutTitles: true,
                    ForSort: false, Short: true));
            return Finish(Context, form);
        }

        /// <summary>
        /// =object.n:acc= — the name in a case (nom, gen, dat, acc, ins, loc), as =object.name= prints it: «ви бачите
        /// =object.n:acc=» → «ви бачите шкіряну броню», «пащеклаца». The player is «ви» in that case: вас, вам, вами.
        /// The game's own parameters of name follow the case: =object.n:gen:withTitles=, single, long, asIfKnown,
        /// stripped. A name the declension cannot read stays as it is (UkrainianCases).
        /// </summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        [VariableParametrizedExample("acc", "пащеклаца:Пащеклаца", new object[] { "Snapjaw" })]
        [VariableParametrizedExample("ins", "пащеклацом:Пащеклацом", new object[] { "Snapjaw" })]
        [VariableParametrizedExample("dat", "вам:Вам", new object[] { "Player" })]
        public static string Name(VariableContext Context, GameObject Object)
        {
            UkCase c = CaseOf(Context);
            if (UkrainianGender.IsSecondPerson(Object)) return Finish(Context, UkrainianCases.You(c));
            string name = Object.GetDisplayName(Stripped: Context.HasParameter("stripped"), WithoutTitles: !Context.HasParameter("withTitles"),
                AsIfKnown: Context.HasParameter("asIfKnown"), Single: Context.HasParameter("single"), IncludeAdjunctNoun: null,
                Cutoff: int.MaxValue, Base: null, Context: null, NoConfusion: Context.HasParameter("noConfusion"), NoColor: false,
                ColorOnly: false, Visible: true, ForSort: false, Short: !Context.HasParameter("long"), BaseOnly: false,
                WithIndefiniteArticle: false, WithDefiniteArticle: false, DefaultDefiniteArticle: null, IndicateHidden: false,
                Capitalize: false, SecondPerson: false, Reflexive: false, AsPossessed: false, AsPossessedBy: null, Reference: false,
                IncludeImplantPrefix: false);
            return Finish(Context, UkrainianCases.Inflect(name, UkrainianGender.OfName(Object), Object.IsCreature, c));
        }

        /// <summary>=hands.n:ins= — a noun the game passes with its pronouns («руками»).</summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        [VariableParametrizedExample("ins", "руками:Руками", new object[] { "руки:plural" })]
        public static string Name(VariableContext Context, GenderedNoun Noun)
        {
            UkGender gender = Noun.Proper ? UkrainianGender.Of(Noun) : UkrainianGender.OfText(Noun.Name);
            bool person = Noun.Pronouns != null && (Noun.Pronouns.Subjective == "he" || Noun.Pronouns.Subjective == "she");
            return Finish(Context, UkrainianCases.Inflect(Noun.Name, gender, person, CaseOf(Context)));
        }

        /// <summary>=limb.n:acc= — a body part, as =limb.name= prints it («ліву руку»).</summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        public static string Name(VariableContext Context, XRL.World.Anatomy.BodyPart Part)
        {
            string name = Part.GetOrdinalName();
            return Finish(Context, UkrainianCases.Inflect(name, UkrainianGender.OfText(name), false, CaseOf(Context)));
        }

        /// <summary>=faction.n:gen= — a faction's name («баратрумитів»).</summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        [VariableParametrizedExample("gen", "баратрумитів:Баратрумитів", new object[] { "Barathrumites" })]
        public static string Name(VariableContext Context, Faction Faction)
        {
            string name = Faction.DisplayName;
            return Finish(Context, UkrainianCases.Inflect(name, UkrainianGender.OfText(name), true, CaseOf(Context)));
        }

        /// <summary>=liquid.n:gen= — a liquid («32 драми прісної води»).</summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        [VariableParametrizedExample("gen", "{{B|води}}:{{B|Води}}", new object[] { "water" })]
        public static string Name(VariableContext Context, XRL.Liquids.BaseLiquid Liquid)
        {
            string name = Liquid.GetName();
            return Finish(Context, UkrainianCases.Inflect(name, UkrainianGender.OfText(name), false, CaseOf(Context)));
        }

        /// <summary>=stat.n:gen= — a statistic, as =stat.name= prints it («+2 до Сили»).</summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        public static string Name(VariableContext Context, XRL.Blueprints.StatisticBlueprint Stat)
        {
            string name = Stat.DisplayName;
            return Finish(Context, UkrainianCases.Inflect(name, UkrainianGender.OfText(name), false, CaseOf(Context)));
        }

        /// <summary>=mutationName.n:gen= — a name the game passes as text: a mutation, a generated name.</summary>
        [VariableReplacer("n", Capitalization = true, Default = "")]
        [VariableParametrizedExample("gen", "Нічного зору:Нічного зору", new object[] { "Нічний зір" })]
        [VariableParametrizedExample("acc", "шкіряну броню:Шкіряну броню", new object[] { "шкіряна броня" })]
        public static string Name(VariableContext Context, string Text)
        {
            return Finish(Context, UkrainianCases.Inflect(Text, UkrainianGender.OfText(Text), false, CaseOf(Context)));
        }

        // the case a name takes, from the first parameter (=object.n:acc=); the nominative if none
        static UkCase CaseOf(VariableContext Context)
        {
            return (Context.Parameters.Count > 0 ? UkrainianCases.Parse(Context.Parameters[0]) : null) ?? UkCase.Nominative;
        }

        [VariableReplacer("plural")]
        public static string Plural(VariableContext Context, int Number)
        {
            return UkrainianForms.ByNumber(Number, Forms(Context));
        }

        [VariableReplacer("plural")]
        public static string Plural(VariableContext Context, long Number)
        {
            return UkrainianForms.ByNumber(Number, Forms(Context));
        }

        static string[] Forms(VariableContext Context)
        {
            string[] forms = new string[Context.Parameters.Count];
            for (int i = 0; i < forms.Length; i++) forms[i] = Context.Parameters[i];
            return forms;
        }

        static string Finish(VariableContext Context, string form)
        {
            return Context.Capitalize ? UkrainianForms.Capitalize(form) : form;
        }
    }
}
