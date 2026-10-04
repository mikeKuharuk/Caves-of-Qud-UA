using System;
using System.Text.RegularExpressions;
using HarmonyLib;
using XRL;
using XRL.World;
using XRL.World.Parts;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The tail of a damage line («You take 5 damage from %t bite.»): what the code passes TakeDamage as its Message,
    /// with %t for whose it was. Physics.ProcessTakeDamage fills such codes in English («your», «the snapjaw's») and
    /// puts its own head before the tail («You take 5 damage», which the Text table has). So the tail is taken over
    /// first: the Damage table gives it in Ukrainian with our grammar for the one who caused the damage
    /// (=object.p:вашого укусу:укусу (@):укусу=) and the one who takes it (=subject…=), and Physics finds no code
    /// left to fill. A melee hit (Combat's own sentence, NoDamageMessage) is not a tail and passes.
    /// </summary>
    [HarmonyPatch(typeof(Physics), nameof(Physics.ProcessTakeDamage))]
    static class DamageTailPatch
    {
        static void Prefix(Physics __instance, Event E)
        {
            if (!Uk.Active || E == null) return;
            try
            {
                string tail = Damage.Tail(E.GetStringParameter("Message", ""), __instance.ParentObject, Damage.Cause(E),
                                          logMiss: !E.HasFlag("NoDamageMessage"));
                if (tail != null) E.SetParameter("Message", tail);
            }
            catch (Exception)
            {
                // a damage line must never stop the damage
            }
        }
    }

    public static class Damage
    {
        // =object.p:<гравець>:<інший>[:<нікого>]=: with no one to blame, the third form, or the second without its name;
        // an empty one takes the space before it along, as the game's culling does with an empty value
        static readonly Regex Possessor = new Regex(@"( ?)=object\.p:([^:=]*)(?::([^:=]*))?(?::([^:=]*))?=");
        static readonly Regex NameMark = new Regex(@"\s*\(@\)|\s*@");

        /// <summary>The object Physics.ProcessTakeDamage fills %t with: whose attack it was.</summary>
        public static GameObject Cause(Event E)
        {
            GameObject source = E.GetGameObjectParameter("Source") ?? E.GetGameObjectParameter("Attacker")
                                ?? E.GetGameObjectParameter("Owner");
            GameObject owner = E.GetGameObjectParameter("Owner") ?? E.GetGameObjectParameter("Attacker");
            return E.GetGameObjectParameter("DescribeAsFrom") ?? (E.HasFlag("Indirect") ? source : null) ?? owner;
        }

        /// <summary>
        /// The Ukrainian for a damage tail, its cause and victim in our grammar; null when the tail is not English
        /// (the string tables gave it) or the Damage table lacks it (logged as a miss when logMiss).
        /// </summary>
        public static string Tail(string message, GameObject victim, GameObject cause, bool logMiss = true)
        {
            if (!CodeText.HasEnglish(message)) return null;
            string template = CodeText.Peek("Damage", message);
            // a tail the table lacks, or one a general key («from %t {0}!», a gas's) took with English in its hole
            if (template == null || template.IndexOf('%') >= 0 || CodeText.HasEnglishWord(template))
            {
                if (logMiss) CodeText.LogMiss("Damage", message);
                return null;
            }
            if (cause == null) template = NoOne(template);
            var builder = template.StartReplace();
            if (victim != null) builder.SetSubject(victim);
            if (cause != null) builder.SetObject(cause);
            return builder.ToString();
        }

        /// <summary>The template with no one to blame: each =object.p:…= becomes its third form, or its second
        /// without the name.</summary>
        public static string NoOne(string template)
        {
            return Possessor.Replace(template, m =>
            {
                string form = m.Groups[4].Success ? m.Groups[4].Value
                              : m.Groups[3].Success ? NameMark.Replace(m.Groups[3].Value, "").Trim()
                              : "";
                return form.Length == 0 ? "" : m.Groups[1].Value + form;
            });
        }
    }
}
