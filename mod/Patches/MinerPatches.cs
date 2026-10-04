using System;
using System.Text.RegularExpressions;
using CavesOfQudUA.Grammar;
using HarmonyLib;
using XRL;
using XRL.Language;
using XRL.World;
using XRL.World.Parts;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// A miner robot names itself after the grenade it lays (Miner.SetupMinerConfiguration): the code cuts the
    /// grenade's name at «grenade» and adds «miner mk II» or «bomber mk II». A Ukrainian name has no «grenade» in it,
    /// so the robot became «{{W|фугасна}} граната Mk I miner mk I», and its ability «Поставити міну [{{W|фугасна}}
    /// граната Mk I Mk I]». Here the grenade's name without «граната» and its mark is the mine's kind («{{W|фугасна}}»):
    /// the robot is «{{W|фугасний}} мінер Mk I» (the words «miner», «bomber» from the Words table), the ability «Поставити
    /// міну [{{W|фугасна}} Mk I]», and the description's mine «{{W|фугасна}} Mk I».
    /// </summary>
    [HarmonyPatch(typeof(Miner), nameof(Miner.SetupMinerConfiguration))]
    static class MinerNamePatch
    {
        static void Prefix(Miner __instance, out bool __state)
        {
            __state = string.IsNullOrEmpty(__instance.MineType);   // the code names the robot only this first time
        }

        static void Postfix(Miner __instance, bool __state)
        {
            if (!Uk.Active || !__state || !Uk.HasCyrillic(__instance.MineName)) return;
            try
            {
                MineName mine = MineName.Of(__instance.MineName);
                if (mine == null) return;
                string roman = XRL.Language.Grammar.GetRomanNumeral(__instance.Mark);
                __instance.MineName = mine.Kind + " ";
                GameObject robot = __instance.ParentObject;
                if (!robot.HasProperName)
                {
                    string noun = CodeTables.Get("Words", __instance.MineTimer == "-1" ? "miner" : "bomber");
                    if (noun != null) robot.Render.DisplayName = mine.Robot(noun) + " Mk " + roman;
                }
                if (__instance.ActivatedAbilityID != Guid.Empty)
                    robot.SetActivatedAbilityDisplayName(__instance.ActivatedAbilityID,
                                                         "Lay Mine [" + __instance.MineName + "mk " + roman + "]");
            }
            catch (Exception) { }   // a name left as the code made it must never break the robot
        }
    }

    /// <summary>The mine in the ability's description: «{{W|фугасна}} Mk I», not «{{W|фугасна}}  mk I».</summary>
    [HarmonyPatch(typeof(Miner), nameof(Miner.CollectStats))]
    static class MinerStatsPatch
    {
        static void Postfix(Miner __instance, Templates.StatCollector stats)
        {
            if (!Uk.Active || stats == null || !Uk.HasCyrillic(__instance.MineName)) return;
            stats.Set("MineDisplayName", __instance.MineName.Trim() + " Mk " + XRL.Language.Grammar.GetRomanNumeral(__instance.Mark));
        }
    }

    /// <summary>
    /// A grenade's Ukrainian name taken apart around «граната»: the words before it (adjectives in the feminine),
    /// those after it («{{normal|нормальності}}»), and whether it is a compound («{{B|ЕМІ}}-граната»).
    /// </summary>
    public sealed class MineName
    {
        public string Before = "", After = "";
        public bool Compound;

        static readonly Regex Mark = new Regex(@"\s+[Mm][Kk]\s+[IVXLC]+\s*$");
        static readonly Regex Grenade = new Regex(@"(^|\s|-)граната(?=\s|$)");
        static readonly Regex FeminineAdjective = new Regex(@"(?<![\p{L}’'-])([\p{L}’'-]*?\p{L})(а|я)(?![\p{L}’'])");

        /// <summary>The parts of a grenade's name, or null when it has no «граната» in it.</summary>
        public static MineName Of(string grenade)
        {
            string name = Mark.Replace(grenade.Trim(), "");
            Match m = Grenade.Match(name);
            if (!m.Success) return null;
            return new MineName
            {
                Before = name.Substring(0, m.Index).Trim(),
                After = name.Substring(m.Index + m.Length).Trim(),
                Compound = m.Groups[1].Value == "-",
            };
        }

        /// <summary>What kind of mine it lays, agreeing with «міна» as the grenade did: «газова {{normal|нормальності}}».</summary>
        public string Kind => Join(Before, After);

        /// <summary>The robot's name with its noun («мінер»): the adjectives before it in the masculine.</summary>
        public string Robot(string noun)
        {
            string before = FeminineAdjective.Replace(Before, m => m.Groups[1].Value + (m.Groups[2].Value == "я" ? "ій" : "ий"));
            return Join(Compound ? before + "-" + noun : Join(before, noun), After);
        }

        static string Join(string a, string b) => a.Length == 0 ? b : b.Length == 0 ? a : a + " " + b;
    }
}
