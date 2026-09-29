using System.Collections.Generic;
using XRL.World;

namespace CavesOfQudUA.Grammar
{
    /// <summary>How a game object agrees in Ukrainian: past tense, adjectives, the verb's number.</summary>
    public static class UkrainianGender
    {
        /// <summary>
        /// The agreement class of an object.
        /// <list type="number">
        /// <item>The player is «ви», so the plural.</item>
        /// <item>A named character agrees with their own gender («Мір’ям пішла»).</item>
        /// <item>Anything else agrees with the grammatical gender of its Ukrainian name: a female snapjaw is still
        /// «пащеклац», so «пащеклац упав».</item>
        /// <item>Without either, the masculine.</item>
        /// </list>
        /// </summary>
        public static UkGender Of(GameObject obj)
        {
            if (obj == null) return UkGender.Masculine;
            if (obj.IsPlayer()) return UkGender.Plural;
            UkGender? personal = Personal(obj);
            UkGender? noun = Noun(obj.GetBlueprint(false));
            if (obj.HasProperName) return personal ?? noun ?? UkGender.Masculine;
            return noun ?? personal ?? UkGender.Masculine;
        }

        static UkGender? Personal(GameObject obj)
        {
            IPronounProvider pronouns = obj.GetPronounProvider();
            if (pronouns != null && !(pronouns is Gender))
            {
                // an explicit pronoun set such as xe/xem: the neuter where a gendered form is unavoidable, as D11 decided
                // for the mopango's ey/em; the ordinary sets follow their subjective pronoun
                switch (pronouns.Subjective)
                {
                    case "he": return UkGender.Masculine;
                    case "she": return UkGender.Feminine;
                    case "they": return UkGender.Plural;
                    case "it": return null;
                }
                return pronouns.Plural ? UkGender.Plural : UkGender.Neuter;
            }
            Gender gender = obj.GetGender();
            return gender == null ? (UkGender?)null : UkrainianForms.FromGameGender(gender.Name, gender.Plural, gender.PseudoPlural);
        }

        static UkGender? Noun(GameObjectBlueprint blueprint)
        {
            for (int depth = 0; blueprint != null && depth < 64; depth++, blueprint = blueprint.ShallowParent)
            {
                if (NounGenders.ByBlueprint.TryGetValue(blueprint.Name, out string letter))
                    return UkrainianForms.FromLetter(letter);
            }
            return null;
        }
    }

    /// <summary>
    /// The grammatical gender of each object's Ukrainian name, from the translators' qud-gender notes. The table is
    /// written by `py tools/qud.py build` into NounGenders.g.cs; without that file it stays empty.
    /// </summary>
    public static partial class NounGenders
    {
        public static readonly Dictionary<string, string> ByBlueprint = new Dictionary<string, string>();

        static NounGenders()
        {
            Fill(ByBlueprint);
        }

        static partial void Fill(Dictionary<string, string> table);
    }
}
