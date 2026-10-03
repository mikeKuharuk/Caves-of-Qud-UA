using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;

static class Tests
{
    static readonly string Managed = Environment.GetEnvironmentVariable("QUD_MANAGED")
        ?? @"D:\Steam\steamapps\common\Caves of Qud\CoQ_Data\Managed";
    static readonly string Root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../.."));
    static int failures;

    static void Eq(string expected, object actual, string what)
    {
        if (expected == (string)actual) return;
        failures++;
        Console.WriteLine($"FAIL {what}: expected «{expected}», got «{actual}»");
    }

    static Assembly game, mod;

    static object Call(string type, string method, params object[] args)
    {
        Type t = game.GetType(type, true);
        MethodInfo m = t.GetMethods(BindingFlags.Public | BindingFlags.Static)
            .First(x => x.Name == method && x.GetParameters().Length == args.Length
                        && x.GetParameters().Zip(args, (p, a) => a == null || p.ParameterType.IsInstanceOfType(a)).All(ok => ok));
        return m.Invoke(null, args);
    }

    static void SetActive(bool? active)
    {
        mod.GetType("CavesOfQudUA.Patches.Uk", true).GetField("ForceActive").SetValue(null, active);
    }

    static int Main()
    {
        Console.OutputEncoding = Encoding.UTF8;
        AppDomain.CurrentDomain.AssemblyResolve += (s, e) =>
        {
            string p = Path.Combine(Managed, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(p) ? Assembly.LoadFrom(p) : null;
        };
        game = Assembly.LoadFrom(Path.Combine(Managed, "Assembly-CSharp.dll"));
        string modDll = Path.Combine(Root, "tools/grammar-build/bin/Debug/netstandard2.0/CavesOfQudUA.Grammar.dll");
        if (!File.Exists(modDll))
        {
            Console.WriteLine("build the mod first: dotnet build tools/grammar-build");
            return 1;
        }
        mod = Assembly.LoadFrom(modDll);

        var harmony = new HarmonyLib.Harmony("CavesOfQudUA.tests");
        harmony.PatchAll(mod);
        Console.WriteLine($"{harmony.GetPatchedMethods().Count()} game methods patched");

        SetActive(true);
        const string G = "XRL.Language.Grammar";
        Eq("сокира", Call(G, "Pluralize", "сокира"), "no English plural on a Ukrainian word");
        Eq("snapjaws", Call(G, "Pluralize", "snapjaw"), "English words keep English rules");
        Eq("пащеклац", Call(G, "MakePossessive", "пащеклац"), "no 's");
        Eq("пащеклац", Call(G, "A", "пащеклац", false), "no article");
        Eq("Пащеклац", Call(G, "A", "пащеклац", true), "no article, capitalised");
        Eq("", Call(G, "IndefiniteArticle", "пащеклац", false), "no indefinite article");
        Eq("Меч з каменю і вогню", Call(G, "MakeTitleCase", "меч з каменю і вогню"), "Ukrainian title case");
        Eq("крила, роги", Call(G, "MakeTheList", new List<string> { "крила", "роги" }, false), "no «the» list");
        Eq("б’є", Call(G, "ThirdPerson", "б’є", false), "no English third person");
        Eq("сидіти", Call(G, "PastTenseOf", "сидіти"), "no English past tense");

        // the code tables: exact keys, patterns, lines, agreement, and the effect patch on a real effect class
        Type tables = mod.GetType("CavesOfQudUA.Grammar.CodeTables", true);
        Type text = mod.GetType("CavesOfQudUA.Patches.CodeText", true);
        void Add(string table, string en, string uk) => tables.GetMethod("Add").Invoke(null, new object[] { table, en, uk });
        string Translate(string table, string en) => (string)text.GetMethod("Translate").Invoke(null, new object[] { table, en, null });
        Add("Test", "Acts semi-randomly.", "Діє майже навмання.");
        Add("Test", "-{0} DV", "-{0} ЗУ");
        Add("Test", "-{0} to all mental attributes", "-{0} до всіх ментальних характеристик");
        Eq("Діє майже навмання.", Translate("Test", "Acts semi-randomly."), "an exact key");
        Eq("-3 ЗУ", Translate("Test", "-3 DV"), "a pattern");
        Eq("Діє майже навмання.\n-3 ЗУ\nsomething new", Translate("Test", "Acts semi-randomly.\n-3 DV\nsomething new"), "line by line");
        Eq("-2 до всіх ментальних характеристик", Translate("Test", "-2 to all mental attributes"), "the longest pattern wins");
        Add("Effects", "{{G|poisoned}}", "{{G|отруєний}}");
        object poisoned = Activator.CreateInstance(game.GetType("XRL.World.Effects.Poisoned", true));
        Eq("{{G|отруєний}}", game.GetType("XRL.World.Effect").GetMethod("GetDescription").Invoke(poisoned, null), "an effect name through the patch");

        SetActive(false);
        Eq("сокираs", Call(G, "Pluralize", "сокира"), "other languages keep the game's behaviour");

        Console.WriteLine(failures == 0 ? "all patch tests passed" : $"{failures} failure(s)");
        return failures == 0 ? 0 : 1;
    }
}
