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

        mod.GetType("CavesOfQudUA.Patches.Uk", true).GetField("OutsideUnity").SetValue(null, true);
        var harmony = new HarmonyLib.Harmony("CavesOfQudUA.tests");
        harmony.PatchAll(mod);
        Console.WriteLine($"{harmony.GetPatchedMethods().Count()} game methods patched");

        // patches whose effect needs Unity: at least each must sit on its method (a renamed method fails here)
        void Patched(string type, string method, string kind)
        {
            MethodBase target = HarmonyLib.AccessTools.Method(game.GetType(type, true), method);
            HarmonyLib.Patches info = target == null ? null : HarmonyLib.Harmony.GetPatchInfo(target);
            int count = info == null ? 0 : kind == "Postfix" ? info.Postfixes.Count : info.Prefixes.Count;
            if (count == 0)
            {
                failures++;
                Console.WriteLine($"FAIL no {kind} on {type}.{method}");
            }
        }
        Patched("Qud.UI.MessageLogWindow", "GameInit", "Postfix");
        Patched("Qud.UI.FilterBarCategoryButton", "SetCategory", "Postfix");

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
        const string X = "XRL.Extensions";
        Eq("5 ходів", Call(X, "Things", 5, "turn", null), "Things: a count the code writes");
        Eq("ще 1 хід", Call(X, "Things", 1, "more turn", "more turns"), "Things: «more»");
        Eq("3 клітинки", Call(X, "Things", 3f, "square", null), "Things on a float");
        Eq("4 widgets", Call(X, "Things", 4, "widget", null), "Things: an English word we do not know");

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

        // the DidX key must be the one tools/qudtr/codescan.py writes (didx_key)
        Type didx = mod.GetType("CavesOfQudUA.Patches.DidX", true);
        Eq("X|die||||!", didx.GetMethod("Key").Invoke(null, new object[] { "X", "die", null, null, null, "!" }), "the DidX key");
        Eq("XZ|sit|down on|||.", didx.GetMethod("Key").Invoke(null, new object[] { "XZ", "sit", "down on", null, null, null }), "a null end mark is a full stop");

        // the Text table at the sinks: a pattern with a Ukrainian name in it, and text with no English passing at once
        Add("Text", "You receive {0}!", "Ви отримуєте: {0}!");
        Eq("Ви отримуєте: сокира!", Translate("Text", "You receive сокира!"), "a sink pattern");
        Eq("Ви вже це знаєте.", Translate("Text", "Ви вже це знаєте."), "no English: unchanged");
        Eq("{{R|Ворог}}", Translate("Text", "{{R|Ворог}}"), "markup alone is not English");

        // a pattern that starts with a hole must not swallow the lines before it
        Add("Test2", "Can't move or attack.", "Не може рухатися чи атакувати.");
        Add("Test2", "{0} DV", "{0} ЗУ");
        Eq("Не може рухатися чи атакувати.\n-5 ЗУ", Translate("Test2", "Can't move or attack.\n-5 DV"), "holes stay within a line");

        // a translation's {n} is the key's {n}: across the fields of a DidX key, out of order, and repeated
        string Lookup(string table, string key) => (string)text.GetMethod("Lookup").Invoke(null, new object[] { table, key });
        Add("Test3", "XZ|juke|{0}, moving||out of {1} way|.", "фінт {0}, з дороги ({1})");
        Eq("фінт на північ, з дороги (its)", Lookup("Test3", "XZ|juke|на північ, moving||out of its way|."), "holes across a DidX key");
        Add("Test4", "{1} hits {0}.", "{0} отримує удар від {1}.");
        Eq("пащеклац отримує удар від Мехмет.", Translate("Test4", "Мехмет hits пащеклац."), "holes out of order");
        Add("Test5", "{0} and {0} again", "{0} двічі");
        Eq("пащеклац двічі", Translate("Test5", "пащеклац and пащеклац again"), "a repeated hole");
        Eq("пащеклац and сокира again", Translate("Test5", "пащеклац and сокира again"), "a repeated hole is the same text");

        // «\r\n» lines (the inventory quick keys): looked up without the «\r», which stays
        Add("Test6", "Inventory quick keys", "Швидкі клавіші інвентаря");
        Add("Test6", "&WCtrl+A&y - Eat", "&WCtrl+A&y - З’їсти");
        Eq("Швидкі клавіші інвентаря\r\n\r\n&WCtrl+A&y - З’їсти\r\n&WCtrl+P&y - Apply",
           Translate("Test6", "Inventory quick keys\r\n\r\n&WCtrl+A&y - Eat\r\n&WCtrl+P&y - Apply"), "\\r\\n lines");

        // a translation counts with a number hole: {0:хід:ходи:ходів}
        Add("Test7", "The dead will be recalled in {0} rounds.", "Мерців буде відкликано через {0} {0:хід:ходи:ходів}.");
        string Recalled(string n) => Translate("Test7", "The dead will be recalled in " + n + " rounds.");
        Eq("Мерців буде відкликано через 1 хід.", Recalled("1"), "1 хід");
        Eq("Мерців буде відкликано через 3 ходи.", Recalled("3"), "3 ходи");
        Eq("Мерців буде відкликано через 12 ходів.", Recalled("12"), "12 ходів");
        Eq("Мерців буде відкликано через {{C|21}} хід.", Recalled("{{C|21}}"), "a number in markup");
        Eq("Мерців буде відкликано через 2.5 ходи.", Recalled("2.5"), "a number that is not whole");

        // a hole that holds a word the code keeps in a constant comes out of the Words table; so do the journal's tabs
        Add("Words", "Locations", "Місця");
        Add("Test8", "You note the location of {0} in the {{W|{1} > Artifacts}} section of your journal.",
            "Ви занотували розташування: {0} — у розділі журналу {{W|{1} > Артефакти}}.");
        Eq("Ви занотували розташування: сокира — у розділі журналу {{W|Місця > Артефакти}}.",
           Translate("Test8", "You note the location of сокира in the {{W|Locations > Artifacts}} section of your journal."),
           "a word from the code in a hole");
        Eq("Місця", Call("XRL.UI.JournalScreen", "GetTabDisplayName", "Locations"), "the journal's title");
        Eq("Some New Tab", Call("XRL.UI.JournalScreen", "GetTabDisplayName", "Some New Tab"), "a tab with no entry stays");

        // a verb the game's data gives: the message's «*» template, with the verb's forms from the Verbs table
        // (the tables load once, at the first lookup, as in the game: every entry goes in before it)
        Add("DidX", "XZ|*|past|||!", "=subject.Name= {v} повз =object.p:вас:ціль (@)=!");
        Add("DidX", "XZ|zap|past|||!", "свій шаблон");
        Add("Verbs", "zing", "дзенькає:дзенькаєте:дзенькають");
        Add("Verbs", "zap", "бахкає:бахкаєте:бахкають");
        Type didxType = mod.GetType("CavesOfQudUA.Patches.DidX", true);
        string Template(string kind, string verb, string prep, string iprep, string extra, string end) =>
            (string)didxType.GetMethod("Template").Invoke(null, new object[] { kind, verb, prep, iprep, extra, end });
        Eq("=subject.Name= =subject.v:дзенькає:дзенькаєте:дзенькають= повз =object.p:вас:ціль (@)=!",
           Template("XZ", "zing", "past", null, null, "!"), "a data verb fills {v}");
        Eq(null, Template("XZ", "quux", "past", null, null, "!"), "a verb the table lacks: no template");
        Eq("свій шаблон", Template("XZ", "zap", "past", null, null, "!"), "a verb's own key comes first");

        SetActive(false);
        Eq("сокираs", Call(G, "Pluralize", "сокира"), "other languages keep the game's behaviour");
        Eq("5 turns", Call(X, "Things", 5, "turn", null), "other languages keep the English count");

        Console.WriteLine(failures == 0 ? "all patch tests passed" : $"{failures} failure(s)");
        return failures == 0 ? 0 : 1;
    }
}
