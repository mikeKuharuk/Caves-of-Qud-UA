using System.Collections.Generic;
using XRL.World;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// Builds object names for Ukrainian. The adjectives the game puts before a name (mods such as «іржавий», the
    /// size, a liquid, «вживлений») are translated in the masculine; here they take the gender of the object
    /// («іржава сокира», «іржаве кресало», «іржаві чоботи»). The other forms come from the translators' uk-forms
    /// notes, which `qud.py build` writes into AdjectiveForms.g.cs; an adjective with no note takes the regular
    /// endings (-ий → -а, -е, -і).
    /// </summary>
    public class UkrainianDescriptionBuilder : DescriptionBuilder
    {
        // entries before the base name (AddBase: 10) are adjectives (AddAdjective: -500)
        const int BaseOrder = 10;

        // the base constructor with these parameters is obsolete (it would skip the translator), so set them here
        public UkrainianDescriptionBuilder(int Cutoff, bool BaseOnly)
        {
            this.Cutoff = Cutoff;
            this.BaseOnly = BaseOnly;
        }

        public override void Resolve()
        {
            base.Resolve();  // adds the size adjective
            UkGender gender = UkrainianGender.OfName(Object);  // a name is third person, even the player's
            if (gender == UkGender.Masculine || Count == 0) return;
            var agreed = new List<KeyValuePair<string, string>>();
            foreach (KeyValuePair<string, int> entry in this)
            {
                if (entry.Value >= BaseOrder) continue;
                string form = UkrainianForms.AgreeAdjective(entry.Key, gender, AdjectiveForms.Get, regular: true);
                if (form != entry.Key) agreed.Add(new KeyValuePair<string, string>(entry.Key, form));
            }
            foreach (KeyValuePair<string, string> pair in agreed)
            {
                int order = this[pair.Key];
                base.Remove(pair.Key);
                if (!ContainsKey(pair.Value)) this[pair.Value] = order;
                if (LastAdded == pair.Key) LastAdded = pair.Value;
            }
        }
    }

    /// <summary>
    /// The other forms of translated adjectives: masculine plain text → [feminine, neuter, plural]. Written by
    /// `py tools/qud.py build` into AdjectiveForms.g.cs from the uk-forms notes; empty without that file.
    /// </summary>
    public static partial class AdjectiveForms
    {
        public static readonly Dictionary<string, string[]> ByMasculine = new Dictionary<string, string[]>();

        static AdjectiveForms()
        {
            Fill(ByMasculine);
        }

        static partial void Fill(Dictionary<string, string[]> table);

        public static string[] Get(string masculine)
        {
            return ByMasculine.TryGetValue(masculine, out string[] forms) ? forms : null;
        }
    }
}
