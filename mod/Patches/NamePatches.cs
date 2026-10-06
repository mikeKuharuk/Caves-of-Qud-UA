using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using HarmonyLib;
using XRL.World;
using XRL.World.Capabilities;
using XRL.World.Parts;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The Tomb's cherubim: the spawners name them in English around a name that is already Ukrainian. CherubimSpawner
    /// takes «mechanical » off the blueprint's name (ours, «механічний херувим-павіан», has none to take), puts the
    /// element's adjective before it (BestowElement: «glass», «jeweled»…) and «mechanical » back: «mechanical glass
    /// механічний херувим-павіан». The name is built again in Ukrainian: «механічний скляний херувим-павіан». The cherub
    /// is masculine, as every blueprint's «херувим-…» is.
    /// </summary>
    [HarmonyPatch(typeof(CherubimSpawner), nameof(CherubimSpawner.HandleEvent), new[] { typeof(BeforeObjectCreatedEvent) })]
    static class CherubNamePatch
    {
        static void Postfix(BeforeObjectCreatedEvent E)
        {
            if (!Uk.Active || E?.ReplacementObject?.Render == null) return;
            E.ReplacementObject.Render.DisplayName = CherubNames.Rebuilt(E.ReplacementObject.Render.DisplayName);
        }
    }

    /// <summary>A hexacherub is a cherub the code renames by replacing «cherub», which a Ukrainian name lacks.</summary>
    [HarmonyPatch(typeof(HexacherubimSpawner), nameof(HexacherubimSpawner.HandleEvent), new[] { typeof(BeforeObjectCreatedEvent) })]
    static class HexacherubNamePatch
    {
        static void Postfix(BeforeObjectCreatedEvent E)
        {
            if (!Uk.Active || E?.ReplacementObject?.Render == null) return;
            E.ReplacementObject.Render.DisplayName = CherubNames.Hexa(E.ReplacementObject.Render.DisplayName);
        }
    }

    public static class CherubNames
    {
        // the adjectives BestowElement puts before a cherub's name, masculine for «херувим»
        static readonly Dictionary<string, string> Elements = new Dictionary<string, string>
        {
            { "glass", "скляний" }, { "jeweled", "самоцвітний" }, { "star", "зоряний" }, { "time", "часовий" },
            { "salt", "соляний" }, { "ice", "крижаний" }, { "learned", "учений" }, { "mighty", "могутній" },
            { "chaotic", "хаотичний" }, { "electric", "електричний" }, { "quickened", "прискорений" },
        };

        /// <summary>«mechanical glass механічний херувим-павіан» → «механічний скляний херувим-павіан».</summary>
        public static string Rebuilt(string name)
        {
            if (string.IsNullOrEmpty(name) || !Uk.HasCyrillic(name)) return name;
            bool mechanical = false;
            var adjectives = new List<string>();
            while (true)
            {
                int space = name.IndexOf(' ');
                if (space <= 0) break;
                string word = name.Substring(0, space);
                if (word == "mechanical") mechanical = true;
                else if (Elements.TryGetValue(word, out string adjective)) adjectives.Add(adjective);
                else break;
                name = name.Substring(space + 1);
            }
            if (mechanical && name.StartsWith("механічн") && name.IndexOf(' ') > 0)
                name = name.Substring(name.IndexOf(' ') + 1);   // the blueprint's own, which goes first again
            if (mechanical) adjectives.Insert(0, "механічний");
            return adjectives.Count == 0 ? name : string.Join(" ", adjectives) + " " + name;
        }

        /// <summary>«херувим-павіан» → «гексахерувим-павіан».</summary>
        public static string Hexa(string name)
        {
            if (string.IsNullOrEmpty(name) || !Uk.HasCyrillic(name) || name.Contains("гексахерувим")) return name;
            int at = name.IndexOf("херувим");
            return at < 0 ? name : name.Substring(0, at) + "гекса" + name.Substring(at);
        }
    }

    /// <summary>
    /// A clone's name: a Cloneling names its clone «clone of » + the name (Cloneling.PerformCloning), and both it and
    /// Cloning.PostprocessClone leave a name alone that has «clone of» in it already. With Ukrainian on, those literals
    /// are «клон »: «клон пащеклац», and a clone of a clone stays «клон пащеклац» (the string tables' own rename,
    /// «клон =subject.refname=», reads the same).
    /// </summary>
    [HarmonyPatch]
    static class CloneNamePatch
    {
        static IEnumerable<MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(Cloneling), nameof(Cloneling.PerformCloning));
            yield return AccessTools.Method(typeof(Cloning), "PostprocessClone");
        }

        static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions, MethodBase __originalMethod)
        {
            MethodInfo local = AccessTools.Method(typeof(CloneNames), nameof(CloneNames.Local));
            // «clone of » before a name only in the Cloneling: Cloning's goes to the string tables' check
            // (Strings.AssertLocalizationMatch), which renames in Ukrainian itself
            bool cloneling = __originalMethod.DeclaringType == typeof(Cloneling);
            foreach (CodeInstruction instruction in instructions)
            {
                yield return instruction;
                if (instruction.opcode == OpCodes.Ldstr && instruction.operand is string text
                    && (text == "clone of" || cloneling && text == "clone of "))
                    yield return new CodeInstruction(OpCodes.Call, local);
            }
        }
    }

    public static class CloneNames
    {
        /// <summary>The literal as the game has it, or in Ukrainian when Ukrainian is on.</summary>
        public static string Local(string text)
        {
            if (!Uk.Active) return text;
            return text == "clone of" || text == "clone of " ? "клон " : text;
        }
    }
}
