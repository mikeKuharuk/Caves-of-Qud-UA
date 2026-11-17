using System;
using System.Text.RegularExpressions;
using CavesOfQudUA.Grammar;
using HarmonyLib;
using XRL;
using XRL.Language;
using XRL.World;
using XRL.World.Parts;
using XRL.World.Parts.Skill;

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
        static void Postfix(Miner __instance)
        {
            if (Uk.Active) MinerNames.Fix(__instance);
        }
    }

    /// <summary>
    /// A robot from a save made before MinerNamePatch (2026-10-04) keeps the code's names: «… граната Mk III miner
    /// mk III», «Поставити міну [… граната Mk III Mk III]». Once its parts are read, it gets ours, as a new one does.
    /// </summary>
    [HarmonyPatch(typeof(GameObject), nameof(GameObject.FinalizeRead))]
    static class MinerLoadPatch
    {
        static void Postfix(GameObject __instance)
        {
            if (!Uk.Active) return;
            Miner miner = __instance.GetPart<Miner>();
            if (miner != null) MinerNames.Fix(miner);
        }
    }

    public static class MinerNames
    {
        /// <summary>
        /// The robot's name, its ability's and its MineName from the grenade's Ukrainian name, while MineName still is
        /// that whole name («… граната Mk I »): the code's first naming, or a save from before. Ours has no «граната»
        /// left, so a second call does nothing.
        /// </summary>
        public static void Fix(Miner miner)
        {
            if (!Uk.HasCyrillic(miner.MineName)) return;
            try
            {
                MineName mine = MineName.Of(miner.MineName);
                if (mine == null) return;
                string roman = XRL.Language.Grammar.GetRomanNumeral(miner.Mark);
                miner.MineName = mine.Kind + " ";
                GameObject robot = miner.ParentObject;
                if (robot == null) return;
                if (!robot.HasProperName)
                {
                    string noun = CodeTables.Get("Words", miner.MineTimer == "-1" ? "miner" : "bomber");
                    if (noun != null) robot.Render.DisplayName = mine.Robot(noun) + " Mk " + roman;
                }
                if (miner.ActivatedAbilityID != Guid.Empty)
                    robot.SetActivatedAbilityDisplayName(miner.ActivatedAbilityID,
                                                         "Lay Mine [" + miner.MineName + "mk " + roman + "]");
            }
            catch (Exception) { }   // a name left as the code made it must never break the robot
        }
    }

    /// <summary>
    /// A grenade laid becomes a mine or a bomb (Tinkering_LayMine.CreateBomb, for the player's skill and the robots
    /// alike): the code puts «mine» or «bomb» in place of «grenade», or after a name without it, which a Ukrainian name
    /// always is: «{{W|фугасна}} граната Mk I mine». Here «граната» becomes the word from Words («міна», «бомба»,
    /// feminine as well, so the adjectives still agree): «{{W|фугасна}} міна Mk I».
    /// </summary>
    [HarmonyPatch(typeof(Tinkering_LayMine), nameof(Tinkering_LayMine.CreateBomb),
                  new[] { typeof(GameObject), typeof(GameObject), typeof(int) })]
    static class LaidMineNamePatch
    {
        static void Postfix(GameObject __result)
        {
            Render render = __result?.Render;
            if (!Uk.Active || render == null || !Uk.HasCyrillic(render.DisplayName)) return;
            render.DisplayName = MineName.Laid(render.DisplayName) ?? render.DisplayName;
        }
    }

    /// <summary>The mine in the ability's description: «{{W|фугасна}} Mk I», not «{{W|фугасна}}  mk I».</summary>
    [HarmonyPatch(typeof(Miner), nameof(Miner.CollectStats))]
    static class MinerStatsPatch
    {
        static void Postfix(Miner __instance, XRL.Templates.StatCollector stats)
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

        /// <summary>
        /// A laid grenade's name as the code leaves it («{{W|фугасна}} граната Mk I mine»), with «граната» made a mine
        /// or a bomb from Words; null when it ends in neither word or Words lacks it.
        /// </summary>
        public static string Laid(string name)
        {
            foreach (string english in new[] { "mine", "bomb" })
            {
                if (!name.EndsWith(" " + english, StringComparison.Ordinal)) continue;
                string word = CodeTables.Get("Words", english);
                if (word == null) return null;
                string bare = name.Substring(0, name.Length - english.Length - 1);
                return Grenade.IsMatch(bare) ? Grenade.Replace(bare, m => m.Groups[1].Value + word, 1) : bare + " " + word;
            }
            return null;
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
