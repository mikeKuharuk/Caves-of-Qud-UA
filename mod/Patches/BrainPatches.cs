using CavesOfQudUA.Grammar;
using HarmonyLib;
using XRL.World;
using XRL.World.Parts;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The lines a creature's brain adds under its description in the look panel (Brain.HandleEvent of
    /// GetShortDescriptionEvent): «Base demeanor: docile», «Engagement style: defensive», «Fighting a snapjaw». The code
    /// appends them to E.Postfix as English literals, past the string tables and AppendRules (RulesPatches), so they
    /// are put into Ukrainian after it has written them; the target a follower fights is named in the instrumental
    /// («Б’ється з пащеклацом»).
    /// </summary>
    [HarmonyPatch(typeof(Brain), nameof(Brain.HandleEvent), new[] { typeof(GetShortDescriptionEvent) })]
    static class BrainDescriptionPatch
    {
        static void Postfix(Brain __instance, GetShortDescriptionEvent E)
        {
            if (!Uk.Active || E?.Postfix == null) return;
            string before = E.Postfix.ToString();
            string after = BrainLines.Translate(before);
            GameObject target = __instance.Target;
            if (target != null && __instance.IsPlayerLed())
            {
                // the name as the brain wrote it (Brain.HandleEvent calls this very overload), then in the instrumental
#pragma warning disable CS0618
                string name = target.an(int.MaxValue, null, null, AsIfKnown: false, Single: false, NoConfusion: false,
                    NoColor: false, Stripped: true);
#pragma warning restore CS0618
                after = after.Replace("\nFighting {{r|" + name + "}}", "\nБ’ється з {{r|"
                    + UkrainianCases.Inflect(name, UkrainianGender.OfName(target), target.IsCreature, UkCase.Instrumental) + "}}");
            }
            if (after == before) return;
            E.Postfix.Clear();
            E.Postfix.Append(after);
        }
    }

    public static class BrainLines
    {
        static readonly string[][] Lines =
        {
            new[] { "\nBase demeanor: {{r|aggressive}}", "\nВдача: {{r|агресивна}}" },
            new[] { "\nBase demeanor: {{g|docile}}", "\nВдача: {{g|сумирна}}" },
            new[] { "\nEngagement style: {{g|defensive}}", "\nМанера бою: {{g|оборонна}}" },
            new[] { "\nEngagement style: {{r|aggressive}}", "\nМанера бою: {{r|наступальна}}" },
        };

        /// <summary>The brain's English lines in text, in Ukrainian.</summary>
        public static string Translate(string text)
        {
            if (string.IsNullOrEmpty(text)) return text;
            foreach (string[] line in Lines)
                text = text.Replace(line[0], line[1]);
            return text;
        }
    }
}
