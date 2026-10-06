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
        Patched("XRL.World.Anatomy.BodyPart", "GetOrdinalName", "Prefix");
        Patched("XRL.World.Anatomy.BodyPart", "GetOrdinalDescription", "Prefix");
        Patched("XRL.World.Parts.ActivatedAbilities", "AddAbility", "Prefix");
        Patched("XRL.World.GameObject", "SetActivatedAbilityDisplayName", "Prefix");
        Patched("XRL.World.Parts.Physics", "ProcessTakeDamage", "Prefix");
        Patched("Qud.API.JournalAPI", "AddAccomplishment", "Prefix");
        Patched("XRL.World.Parts.ActivatedAbilityEntry", "Read", "Postfix");
        Patched("XRL.UI.SPNode", "ModernUIText", "Postfix");
        Patched("XRL.World.Anatomy.BodyPart", "ReadValues", "Postfix");
        Patched("Qud.UI.CharacterStatusScreen", "UpdateViewFromData", "Postfix");
        Patched("Qud.UI.CharacterStatusScreen", "HandleHighlightMutation", "Postfix");
        Patched("Qud.UI.WorldGenerationScreen", "Show", "Postfix");
        int describes = game.GetType("XRL.World.GameObject", true).GetMethods()
            .Count(m => m.Name == "DescribeActivatedAbility" && HarmonyLib.Harmony.GetPatchInfo(m)?.Postfixes.Count > 0);
        Eq("3", describes.ToString(), "every DescribeActivatedAbility is patched");

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

        // body parts' sides on a Ukrainian name, the game's own on an English one (1 left, 2 right, 4 upper, 64 hind)
        Type laterality = game.GetType("XRL.World.Capabilities.Laterality", true);
        MethodInfo withSide = laterality.GetMethods().First(m => m.Name == "WithLateralityAdjective" && m.GetParameters().Length == 4);
        string Sided(string noun, int bits, bool capitalized) => (string)withSide.Invoke(null, new object[] { noun, bits, null, capitalized });
        Eq("ліва рука", Sided("рука", 1, false), "left arm");
        Eq("Верхній правий ріг", Sided("Ріг", 4 | 2, true), "Upper Right Horn");
        // (an English name goes to the game's own code, which needs the string tables and so Unity: not testable here)
        Eq("рука", Call("XRL.World.Capabilities.Laterality", "StripLateralityAdjective", "ліва рука", 1, false), "the sides taken off");

        // a slot whose type puts English before it («Worn on Back», Bodies.xml DescriptionPrefix): the part alone
        Type bodyPartType = game.GetType("XRL.World.Anatomy.BodyPart", true);
        object slot = System.Runtime.CompilerServices.RuntimeHelpers.GetUninitializedObject(bodyPartType);
        void SetMember(string member, object value)
        {
            FieldInfo field = bodyPartType.GetField(member);
            if (field != null) field.SetValue(slot, value);
            else bodyPartType.GetProperty(member).SetValue(slot, value);
        }
        string Describe(string method) => (string)bodyPartType.GetMethod(method, Type.EmptyTypes).Invoke(slot, null);
        SetMember("DescriptionPrefix", "Worn on");
        SetMember("IgnorePosition", true);
        SetMember("Abstract", true);   // no category colour
        SetMember("Description", "Спина");
        Eq("Спина", Describe("GetCardinalDescription"), "an English prefix before a Ukrainian slot");
        Eq("Спина", Describe("GetOrdinalDescription"), "an English prefix before a Ukrainian slot, ordinal");
        SetMember("Description", "Back");
        Eq("Worn on Back", Describe("GetCardinalDescription"), "an English slot keeps its prefix");

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

        // a melee hit as Combat builds it: a colour code in markup, the pronoun hole before a weapon of two words
        Add("Test11", "{0} hits {{{1}|(x{2})}} for {3} damage with {4} {5}. [{6}]",
            "{0} влучає у вас {{{1}|(x{2})}} і завдає {3} шкоди ({5}). [{6}]");
        Eq("Пащеклац влучає у вас {{y|(x1)}} і завдає 3 шкоди (гострі щелепи). [12]",
           Translate("Test11", "Пащеклац hits {{y|(x1)}} for 3 damage with its гострі щелепи. [12]"), "a melee hit");

        // a damage line's tail: with no one to blame, =object.p:…= takes its third form (and an empty one its space)
        Type damage = mod.GetType("CavesOfQudUA.Patches.Damage", true);
        string NoOne(string template) => (string)damage.GetMethod("NoOne").Invoke(null, new object[] { template });
        Eq("від атаки.", NoOne("від =object.p:вашої атаки:атаки (@):атаки=."), "no one: the third form");
        Eq("від атаки.", NoOne("від =object.p:вашої атаки:атаки (@)=."), "no one: the second form without the name");
        Eq("від вогню!", NoOne("від вогню =object.p:(ваш):(@):=!"), "no one: nothing, and no space before «!»");
        // a general key takes a tail it does not know, with its %t or English in a hole: the tail stays as the game has it
        Add("Damage", "from {0}!", "({0})!");
        string Tail(string message) => (string)damage.GetMethod("Tail").Invoke(null, new object[] { message, null, null, true });
        Eq(null, Tail("from %t mystery!"), "a %t or an English word left in a hole is no translation");
        Eq(null, Tail("from a mystery!"), "an English word left in a hole is no translation");
        Type codeText = mod.GetType("CavesOfQudUA.Patches.CodeText", true);
        Eq("False", codeText.GetMethod("HasEnglishWord").Invoke(null, new object[] { "від =object.p:вашої атаки:атаки (@)=." }).ToString(),
           "our grammar variables are not English");
        Eq(null, Tail("від укусу."), "a tail the string tables gave passes");
        // a key's name in a button and a variable the game has not replaced are not English to translate
        string HasEnglish(string s) => codeText.GetMethod("HasEnglish").Invoke(null, new object[] { s }).ToString();
        Eq("False", HasEnglish("{{W|[{{keybind|Esc}}]}} {{y|Скасувати}}"), "a key's name");
        Eq("False", HasEnglish("Кидок проти кровотечі: =statistics[Toughness].title= "), "an unreplaced variable");
        Eq("True", HasEnglish("{{W|[{{keybind|Esc}}]}} {{y|Cancel}}"), "English beside a key's name");

        // an ability's description built again from its template: the template's lines pass, the code's English
        // lines under it go through the table (the real Abilities table has them: tools/qudtr/codescan.postfix_keys)
        Add("Test12", "Cooldown reduced by {0} due to {1}.", "Перезаряджання: на {0} менше ({1}).");
        Add("Test12", "{0}: {1}", "should never match a Ukrainian line");
        Eq("Перезаряджання: 95 ход.\nПерезаряджання: на 5 менше (Сила волі: висока).",
           Translate("Test12", "Перезаряджання: 95 ход.\nCooldown reduced by 5 due to Сила волі: висока."), "a line under a description");
        Eq("Перезаряджання: на 2 менше (Сила волі: висока).",
           Translate("Abilities", "Cooldown reduced by 2 due to Сила волі: висока."), "the Abilities table has the cooldown line");

        // the player as X.Does("verb") writes them, «Ви» and the English verb: looked up as «You», before the plural
        // key would take «Ви» into its hole (tools/qudtr/codescan.py, does_forms)
        Add("Test13", "You hit {0}.", "Ви влучаєте в ціль ({0}).");
        Add("Test13", "{0} hit {1}.", "{0} влучають у ціль ({1}).");
        Add("Test13", "Rifling through {0}, you find nothing.", "Перебираючи {0}, ви нічого не знаходите.");
        Eq("Ви влучаєте в ціль (пащеклац).", Translate("Test13", "Ви hit пащеклац."), "the player's «Ви» before an English verb");
        Eq("Пащеклаци влучають у ціль (Ви).", Translate("Test13", "Пащеклаци hit Ви."), "«Ви» with no English after it stays");
        Eq("Перебираючи сміття, ви нічого не знаходите.", Translate("Test13", "Rifling through сміття, ви find nothing."),
           "«ви» inside a sentence");
        Eq("Перебираючи сміття, ви нічого не знаходите.\nПеребираючи мотлох, ви нічого не знаходите.",
           Translate("Test13", "Rifling through сміття, ви find nothing.\nRifling through мотлох, ви find nothing."), "line by line");
        // the real table: a critical hit of the player's missile, the adverb out of the Words table
        Eq("Ви критично влучаєте в ціль (пащеклац)! (x2)", Translate("Text", "Ви critically hit пащеклац! (x2)"),
           "the Text table's player key");
        Eq("Пащеклац критично влучає у вас! (x2)", Translate("Text", "Пащеклац critically hits you! (x2)"), "and anyone else's");
        // GameObject's own Does (no X before it), a name in a colour, a state word out of Words
        Eq("Ви відновлюєте 5 очок здоров’я.", Translate("Text", "Ви heal for 5 hit points."), "a Does with no X, counted");
        Eq("Ви перемикаєте {{c|Спринт}}: увімкнено.", Translate("Text", "You toggle {{c|Спринт}} on."), "a name in a colour");
        Eq("Ви знерухомлені!", Translate("Text", "You are immobilized!"), "a state word");
        // the verb alone (X.GetVerb), after a name or after the code's own «You»
        Eq("Стріла не пробиває вашу броню!", Translate("Text", "Стріла fails to penetrate your armor!"), "a GetVerb key");
        Eq("Вас трохи нудить.", Translate("Text", "You feel a little queasy."), "the player's GetVerb key");
        // an owner's noun (X.Poss): the owner's name with no «'s» (MakePossessive leaves ours), the player's «Your»
        Eq("Атака (Пащеклац) проходить крізь ціль (сокира)!", Translate("Text", "Пащеклац attack passes through сокира!"),
           "a Poss key");
        Eq("З вашого носа починає текти.", Translate("Text", "Your nose begins bleeding."), "the player's Poss key");
        // the game info (XRLCore): its lines indented for the block are keys, the mode out of the Words table
        Eq("\n\n           Гра: класичний режим.\n\n           Хід 1120\n\n          Сід світу: 12345     \n\n\n   ",
           Translate("Text", "\n\n           Classic mode.\n\n           Turn 1120\n\n          World seed: 12345     \n\n\n   "),
           "the game info");
        // (a tail that renders goes through the game's template engine, which is empty outside the game)

        // a statistic's ID in a hole: the string tables' title for it; with no blueprints loaded, the ID as it is
        Add("Test9", "Fails a {0} save.", "Провалює кидок «{0}».");
        Add("Test10", "Passes a {0} save.", "Проходить кидок «{0}».");
        Eq("Провалює кидок «Toughness».", Translate("Test9", "Fails a Toughness save."), "a statistic with no blueprints");
        FieldInfo statTitle = text.GetField("StatTitle");
        object gameStatTitle = statTitle.GetValue(null);
        statTitle.SetValue(null, (Func<string, string>)(v => v == "Toughness" ? "Витривалість" : null));
        Eq("Проходить кидок «Витривалість».", Translate("Test10", "Passes a Toughness save."), "a statistic's title");
        // a statistic's value a description shows: a word from the Words table, a statistic before its number
        Type statValues = mod.GetType("CavesOfQudUA.Patches.StatValues", true);
        string Shown(string v) => (string)statValues.GetMethod("Shown").Invoke(null, new object[] { v });
        Add("Words", "out of reach", "поза досяжністю");
        Eq("поза досяжністю", Shown("out of reach"), "a value from the Words table");
        Eq("Витривалість 21", Shown("Toughness 21"), "a statistic and its number");
        Eq(null, Shown("Wisdom 21"), "a statistic with no title stays");
        Eq(null, Shown("1d8+2"), "dice are no English");
        statTitle.SetValue(null, gameStatTitle);
        Patched("XRL.World.Text.Delegates.XMLTemplateReplacers", "Value", "Prefix");

        // a miner robot named after its grenade: the kind of mine, and the robot with the adjectives in the masculine
        Patched("XRL.World.Parts.Miner", "SetupMinerConfiguration", "Postfix");
        Patched("XRL.World.Parts.Miner", "CollectStats", "Postfix");
        Type mineName = mod.GetType("CavesOfQudUA.Patches.MineName", true);
        object Mine(string grenade) => mineName.GetMethod("Of").Invoke(null, new object[] { grenade });
        string Kind(string grenade) => (string)mineName.GetProperty("Kind").GetValue(Mine(grenade));
        string Robot(string grenade, string noun) => (string)mineName.GetMethod("Robot").Invoke(Mine(grenade), new object[] { noun });
        Eq("{{W|фугасна}}", Kind("{{W|фугасна}} граната Mk I "), "the kind of a mine");
        Eq("{{W|фугасний}} мінер", Robot("{{W|фугасна}} граната Mk I", "мінер"), "a miner");
        Eq("{{w|снодійний}} газовий підривник", Robot("{{w|снодійна}} газова граната Mk III", "підривник"), "two adjectives");
        Eq("{{B|ЕМІ}}-мінер", Robot("{{B|ЕМІ}}-граната Mk II", "мінер"), "a compound");
        Eq("газовий мінер {{normal|нормальності}}", Robot("газова граната {{normal|нормальності}} Mk I", "мінер"), "words after");
        Eq("мінер {{b|сповільнення часу}}", Robot("граната {{b|сповільнення часу}} Mk I", "мінер"), "no adjective");
        Eq("пружинно-турельний мінер", Robot("пружинно-турельна граната Mk I", "мінер"), "a hyphenated adjective");
        Eq(null, Mine("гранатомет Mk I"), "no «граната», no name");
        // a laid grenade: «граната» becomes a mine or a bomb (the real Words table has both)
        MethodInfo createBomb = game.GetType("XRL.World.Parts.Skill.Tinkering_LayMine", true).GetMethods()
            .First(m => m.Name == "CreateBomb" && m.GetParameters()[0].ParameterType.Name == "GameObject");
        Eq("1", (HarmonyLib.Harmony.GetPatchInfo(createBomb)?.Postfixes.Count ?? 0).ToString(), "CreateBomb(GameObject…) is patched");
        string Laid(string name) => (string)mineName.GetMethod("Laid").Invoke(null, new object[] { name });
        Eq("{{W|фугасна}} міна Mk I", Laid("{{W|фугасна}} граната Mk I mine"), "a laid mine");
        Eq("{{B|ЕМІ}}-бомба Mk II", Laid("{{B|ЕМІ}}-граната Mk II bomb"), "a laid bomb, a compound");
        Eq("пастка міна", Laid("пастка mine"), "no «граната»: the word after the name");
        Eq(null, Laid("{{W|фугасна}} граната Mk I"), "nothing laid, nothing changed");

        // the rules lines of a description pass Extensions.AppendRules, which takes them through the Rules table
        Add("Rules", "Glinting: +{0} to shine", "Блискучий: +{0} до сяйва");
        MethodInfo appendRules = game.GetType("XRL.Extensions", true).GetMethods()
            .First(m => m.Name == "AppendRules" && m.GetParameters().Select(p => p.ParameterType)
                            .SequenceEqual(new[] { typeof(StringBuilder), typeof(string) }));
        Eq("\n{{rules|Блискучий: +2 до сяйва}}", appendRules.Invoke(null, new object[] { new StringBuilder(), "Glinting: +2 to shine" }).ToString(),
           "a rules line");
        int rulesOverloads = game.GetType("XRL.Extensions", true).GetMethods()
            .Count(m => m.Name == "AppendRules" && HarmonyLib.Harmony.GetPatchInfo(m)?.Prefixes.Count > 0);
        Eq("5", rulesOverloads.ToString(), "every AppendRules that takes the text is patched");

        // what the code adds to a name comes into our DescriptionBuilder through the Fragments table
        Add("Fragments", "glinting", "блискучий");
        Add("Fragments", "[{{B|perched on {0}}}]", "[{{B|на сідалі: {0}}}]");
        Type builderType = mod.GetType("CavesOfQudUA.Grammar.UkrainianDescriptionBuilder", true);
        object builder = Activator.CreateInstance(builderType, int.MaxValue, false);
        builderType.GetMethod("AddAdjective").Invoke(builder, new object[] { "glinting", 0 });
        builderType.GetMethod("AddTag").Invoke(builder, new object[] { "[{{B|perched on гілка}}]", 0 });
        builderType.GetMethod("AddTag").Invoke(builder, new object[] { "[{{K|порожньо}}]", 0 });
        var parts = (IDictionary<string, int>)builder;
        Eq("[{{B|на сідалі: гілка}}]|[{{K|порожньо}}]|блискучий", string.Join("|", parts.Keys.OrderBy(k => k, StringComparer.Ordinal)),
           "a name's fragments: an adjective, a tag by pattern, one already Ukrainian");

        SetActive(false);
        Eq("сокираs", Call(G, "Pluralize", "сокира"), "other languages keep the game's behaviour");
        Eq("5 turns", Call(X, "Things", 5, "turn", null), "other languages keep the English count");

        Console.WriteLine(failures == 0 ? "all patch tests passed" : $"{failures} failure(s)");
        return failures == 0 ? 0 : 1;
    }
}
