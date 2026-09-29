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
    /// A capital first letter (=subject.V:…=, =subject.G:…=) capitalizes the chosen form.
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
