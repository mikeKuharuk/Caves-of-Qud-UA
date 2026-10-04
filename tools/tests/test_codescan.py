"""codescan: English the game's C# writes, found in decompiled code, as code-table keys."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import checks, codescan, po  # noqa: E402

EFFECT = '''using System;
namespace XRL.World.Effects;
public class Confused : Effect
{
    public Confused(int Duration, string DisplayName = "{{R|very confused}}")
    {
        base.Duration = Duration;
        DisplayName = "{{R|confused}}";
    }
    public override string GetDetails()
    {
        using TextBuilder textBuilder = TextBuilder.Get();
        textBuilder.Append("Acts semi-randomly.\n-").Append(Level).Append(" DV");
        if (MentalPenalty > 0)
        {
            textBuilder.Compound("-", "\n").Append(MentalPenalty).Append(" to all mental attributes");
        }
        return textBuilder.ToString();
    }
    public override string GetStateDescription()
    {
        return (Level > 2) ? "{{R|badly confused}}" : _S("Confused State", "{{R|confused}}");
    }
}
'''


class Patterns(unittest.TestCase):
    def test_literals_holes_ternaries_and_coalescing(self):
        self.assertEqual(codescan.patterns('"{{G|poisoned}}"'), ["{{G|poisoned}}"])
        self.assertEqual([codescan.number_holes(p) for p in codescan.patterns('"-" + Penalty + " Quickness"')],
                         ["-{0} Quickness"])
        self.assertEqual(codescan.patterns('(Level > 1) ? "a" : "b"'), ["a", "b"])
        self.assertEqual(codescan.patterns('x?.Name ?? "default"'), ["default"])
        self.assertEqual(codescan.patterns('_S("ctx", "already in the tables")'), [])

    def test_a_ternary_inside_a_concatenation(self):
        expr = '"Shines" + ((chance < 100) ? (" " + chance + "% of the time") : "") + "."'
        # one hole for the tables scanned before, both branches for the new ones
        self.assertEqual([codescan.number_holes(p) for p in codescan.patterns(expr)], ["Shines{0}."])
        self.assertEqual([codescan.number_holes(p) for p in codescan.patterns(expr, nested=True)],
                         ["Shines {0}% of the time.", "Shines."])
        # a branch with no text of its own is a hole
        self.assertEqual([codescan.number_holes(p) for p in codescan.patterns('"by " + (named ? Name : "your " + Base)',
                                                                              nested=True)],
                         ["by {0}", "by your {0}"])

    def test_an_empty_append_line_adds_the_break_alone(self):
        src = 'void M()\n{\n\tsb.Append("Shiny").AppendLine().Append("Dull");\n\tShow(sb.ToString());\n}'
        masked = codescan.mask(src)
        self.assertEqual(codescan.resolve(src, masked, src.index("Show"), "sb.ToString()"), ["Shiny\nDull"])

    def test_literal_escapes(self):
        self.assertEqual(codescan.literal_value(r'"a\nb\"c"'), 'a\nb"c')
        self.assertEqual(codescan.literal_value('@"say ""hi"""'), 'say "hi"')


class Effects(unittest.TestCase):
    def test_names_and_detail_lines(self):
        with tempfile.TemporaryDirectory() as d:
            folder = pathlib.Path(d) / "XRL.World.Effects"
            folder.mkdir()
            (folder / "Confused.cs").write_text(EFFECT, encoding="utf-8")
            keys = {e.key: e.where for e in codescan.scan_effects(pathlib.Path(d))}
        self.assertEqual(keys.get("{{R|confused}}"), "Confused.DisplayName")
        self.assertNotIn("{{R|very confused}}", keys)          # a parameter's default value, not an assignment
        self.assertIn("Acts semi-randomly.", keys)
        self.assertIn("-{0} DV", keys)
        self.assertIn("-{0} to all mental attributes", keys)   # Compound puts its separator first: its own line
        self.assertIn("{{R|badly confused}}", keys)
        self.assertNotIn("{{R|confused}}", [k for k, w in keys.items() if w.endswith("GetStateDescription")])


class Holes(unittest.TestCase):
    def test_crlf_lines_keep_no_cr(self):
        # the key is what CodeText looks up: a line without its «\r»
        self.assertEqual(codescan.lines_of("Inventory quick keys\r\n\r\n&WCtrl+A&y - Eat\r\n&WCtrl+P&y - Apply"),
                         ["Inventory quick keys", "&WCtrl+A&y - Eat", "&WCtrl+P&y - Apply"])

    def test_every_hole_must_stay(self):
        self.assertEqual(checks.check("-{0} DV", "-{0} ЗУ"), [])
        self.assertIn("code-hole", {i.code for i in checks.check("-{0} DV", "-ЗУ")})
        self.assertIn("code-hole", {i.code for i in checks.check("-{0} DV", "-{1} ЗУ") if i.severity == "error"})
        self.assertEqual(checks.check("{{G|poisoned}}", "{{G|отруєний}}"), [])
        # a hole right before the end of markup is a hole too
        self.assertIn("code-hole", {i.code for i in checks.check("You gain {{C|{0}}} XP!", "Ви отримуєте {{C|}} ОД!")})

    def test_a_word_counted_with_a_hole(self):
        self.assertEqual(checks.check("in {0} rounds.", "через {0} {0:хід:ходи:ходів}."), [])
        errors = lambda uk: {i.code for i in checks.check("in {0} rounds.", uk) if i.severity == "error"}
        self.assertIn("code-hole", errors("через {0} {1:хід:ходи:ходів}."))   # no {1} in the source
        self.assertIn("code-hole", errors("через {0} {0:ходи:ходів}."))       # two forms


DIDX = """public class Healing : Effect
{
    public override void Apply()
    {
        DidX("begin", "healing");
        DidX("die", null, "!");
        DidXToY("strike", "at", target, "with " + weapon.its + " fist", EndMark: "!");
        IComponent<GameObject>.XDidYToZ(Actor, "kick", Object);
        Messaging.WDidXToYWithZ(Actor, "staunch", Object, "with", Bandage);
        DidXToY("juke", Directions.GetDirectionDescription(text) + ", moving", Object, "out of " + ParentObject.its + " way", null, null, null, ParentObject);
    }
    public void DidX(string Verb, string Extra = null) { }
}
"""


class DidXScan(unittest.TestCase):
    def test_calls_become_runtime_keys(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Healing.cs").write_text(DIDX, encoding="utf-8")
            found = {k: e for k, e, w in codescan.scan_didx(pathlib.Path(d))}
        self.assertEqual(found.get("X|begin|||healing|."), "<subject> begin healing.")
        self.assertIn("X|die||||!", found)
        self.assertEqual(found.get("XZ|strike|at||with {0} fist|!"), "<subject> strike at <object> with {0} fist!")
        self.assertIn("XZ|kick||||.", found)
        self.assertEqual(found.get("WXZ|staunch||with||."), "<subject> staunch <object> with <indirect>.")

    def test_holes_are_counted_across_the_key(self):
        # the run time fills a translation's {n} with the key's {n}: two fields must not both have a {0}
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Healing.cs").write_text(DIDX, encoding="utf-8")
            found = {k: e for k, e, w in codescan.scan_didx(pathlib.Path(d))}
        self.assertEqual(found.get("XZ|juke|{0}, moving||out of {1} way|."),
                         "<subject> juke {0}, moving <object> out of {1} way.")

    def test_a_template_with_our_variables_passes(self):
        self.assertEqual(checks.check("<subject> die!", "=subject.Name= =subject.v:помирає:помираєте:помирають=!"), [])

    def test_computed_fields_and_a_null_preposition(self):
        src = """public class Bleeding : Effect
{
    public string Text = "immobilized";
    public Bleeding()
    {
        DisplayName = "{{r|bleeding}}";
    }
    public void Tick()
    {
        DidX("begin", DisplayNameStripped, "!");
        DidX("are", Text, "!");
        IComponent<GameObject>.XDidYToZ(ParentObject, "give", null, The.Player, "a treat");
    }
}
"""
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Bleeding.cs").write_text(src, encoding="utf-8")
            found = {k for k, e, w in codescan.scan_didx(pathlib.Path(d))}
        # a field: what the class assigns it (markup off for «…Stripped»), and one hole for what it computes
        self.assertTrue({"X|begin|||bleeding|!", "X|begin|||{0}|!", "X|are|||immobilized|!", "X|are|||{0}|!"} <= found)
        # a bare null second is the preposition, not the object
        self.assertIn("XZ|give|||a treat|.", found)

    def test_verbs_the_data_gives(self):
        projectile = """public class Projectile : IPart
{
    public string PassByVerb = IComponent<GameObject>._S("Projectile Default PassByVerb", "whiz");
}
"""
        missile = """public class MissileWeapon : IPart
{
    public void Fly(Projectile projectile, bool flag)
    {
        string passByVerb = projectile.PassByVerb;
        IComponent<GameObject>.XDidYToZ(Object3, passByVerb, "past", target, null, "!", null, null, target);
        IComponent<GameObject>.XDidYToZ(Object3, passByVerb, "zoom", target, null, "!", null, null, target, null, UseFullNames: false, IndefiniteSubject: false, IndefiniteObject: false, IndefiniteObjectForOthers: false, PossessiveObject: false, null, null, null, DescribeSubjectDirection: false, DescribeSubjectDirectionLate: false, AlwaysVisible: false, FromDialog: false, UsePopup: false, null, "Pass By Message");
        DidX(flag ? "feed" : "apply", null, ".");
    }
}
"""
        blueprints = {"Items.xml": '<objects><object Name="Bolt"><part Name="Projectile" PassByVerb="streak" />'
                                   '</object></objects>'}
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Projectile.cs").write_text(projectile, encoding="utf-8")
            (pathlib.Path(d) / "MissileWeapon.cs").write_text(missile, encoding="utf-8")
            found = {k for k, e, w in codescan.scan_didx(pathlib.Path(d), blueprints)}
            verbs = {v.key for v in codescan.scan_verbs(pathlib.Path(d), blueprints)}
        # a verb the data gives: the message keyed by the slot, the verbs into the Verbs table
        self.assertIn("XZ|*|past|||!", found)
        self.assertEqual(verbs, {"whiz", "streak"})
        # a call the player reads through its _T twin gets no slot key
        self.assertNotIn("XZ|*|zoom|||!", found)
        # literals the code chooses between are keys as any verb
        self.assertTrue({"X|feed||||.", "X|apply||||."} <= found)

    def test_verb_slots_and_forms_are_checked(self):
        self.assertEqual(checks.check("<subject> <verb> past <object>!", "=subject.Name= {v} повз вас!"), [])
        errors = lambda en, uk: {i.code for i in checks.check(en, uk) if i.severity == "error"}
        self.assertIn("verb-slot", errors("<subject> <verb> past <object>!", "=subject.Name= свистить повз вас!"))
        self.assertIn("verb-slot", errors("<subject> die!", "=subject.Name= {v}!"))
        entry = po.Entry(msgid="whiz", msgstr="свистить:свистите", msgctxt="entry[Key=whiz]@Forms")
        self.assertIn("verb-forms", {i.code for i in checks.check_entry(entry)})
        entry.msgstr = "свистить:свистите:свистять"
        self.assertEqual(checks.check_entry(entry), [])


class WordsScan(unittest.TestCase):
    def test_constants_the_player_reads(self):
        sources = {
            "XRL.UI/JournalScreen.cs": 'public static readonly string STR_LOCATIONS = "Locations";\n'
                                       'public static string NotAConstant = "Other";\n',
            "XRL.World.Parts/LongBladesCore.cs": 'public const string STR_DEFENSIVE = "defensive";\n',
            "XRL.World.Parts.Mutation/FireBreather.cs": 'public override string GetBreathName()\n\t{\n\t\treturn "fire";\n\t}\n',
            "XRL.World.Parts.Mutation/BreatherBase.cs": 'public virtual string GetBreathName()\n\t{\n\t\treturn "base";\n\t}\n',
        }
        with tempfile.TemporaryDirectory() as d:
            for rel, text in sources.items():
                (pathlib.Path(d) / rel).parent.mkdir(parents=True, exist_ok=True)
                (pathlib.Path(d) / rel).write_text(text, encoding="utf-8")
            found = {e.key for e in codescan.scan_words(pathlib.Path(d))}
        self.assertEqual(found, {"Locations", "defensive", "fire"})


class AbilitiesScan(unittest.TestCase):
    # made-up classes in the shapes the game's code takes
    SOURCES = {
        "Glower.cs": """public class Persuasion_Glower : BaseSkill
{
	public override bool AddSkill(GameObject GO)
	{
		AbilityID = AddMyActivatedAbility("Glower", "CommandGlower", "Skills", "You glower.", "*");
		OtherID = AddMyActivatedAbility(IComponent<GameObject>._S("Ctx", "Sprouting"), "CommandSprout", "Mental Mutations");
		return true;
	}
}""",
        # a rename with a count, and a builder with a ternary and a char
        "Copier.cs": """public class Copier : IPart
{
	public void Sync()
	{
		SetMyActivatedAbilityDisplayName(AbilityID, "Copy [" + CopiesLeft + " left]");
	}

	public string GetAbilityName(GameObject Actor = null)
	{
		using TextBuilder sb = TextBuilder.Get();
		sb.Append(On ? "Switch off" : "Switch on").Append(' ').Append(ItemName);
		return sb.ToString();
	}

	public void Add(GameObject Actor)
	{
		AbilityID = Actor.AddActivatedAbility(GetAbilityName(Actor), "CommandToggle", "Items");
	}
}""",
        # a field a subclass sets, a method a subclass overrides, a parameter passed through
        "Spitter.cs": """public class Spitter : BaseMutation
{
	public string CommandName;

	public virtual string GetCommandDisplayName()
	{
		return "[Spitter::GetCommandDisplayName]";
	}

	public override bool Mutate(GameObject GO, int Level)
	{
		AbilityID = AddMyActivatedAbility(CommandName, EventKey, "Physical Mutations", null, "*");
		OtherID = AddMyActivatedAbility(GetCommandDisplayName(), EventKey, "Physical Mutations");
		return base.Mutate(GO, Level);
	}
}""",
        "SeedSpitter.cs": """public class SeedSpitter : Spitter
{
	public SeedSpitter()
	{
		CommandName = "Spit Seeds";
	}

	public override string GetCommandDisplayName()
	{
		return "Spit Pits";
	}
}""",
        "IComponent.cs": """public class IComponent<T>
{
	public Guid AddMyActivatedAbility(string Name, string Command, string Class, string Description = null)
	{
		return who.AddActivatedAbility(Name, Command, Class, Description);
	}
}""",
        # what a subclass calls Name is not what callers pass in
        "Banner.cs": """public class Banner : IComponent<GameObject>
{
	public string Name = "Not An Ability";
}""",
        # a local that grows: «Glide», then «Glide (…)»
        "Gliding.cs": """public static class Gliding
{
	public static bool Setup(GameObject Object, IGlideSource Source)
	{
		string text = "Glide";
		if (Source.Description != null)
		{
			text = text + " (" + Source.Description + ")";
		}
		Source.AbilityID = Object.AddActivatedAbility(text, Source.Command, Source.Class);
		return true;
	}
}""",
    }

    def test_names_the_code_gives_and_none_the_string_tables_do(self):
        with tempfile.TemporaryDirectory() as d:
            for rel, text in self.SOURCES.items():
                (pathlib.Path(d) / rel).write_text(text, encoding="utf-8")
            found = {e.key for e in codescan.scan_abilities(pathlib.Path(d))}
        self.assertEqual(found, {"Glower", "You glower.", "Copy [{0} left]", "Switch on {0}", "Switch off {0}",
                                 "Spit Seeds", "Spit Pits", "Glide", "Glide ({0})", "Jump"})


class FragmentsScan(unittest.TestCase):
    # made-up parts in the shapes the game's code takes
    SOURCES = {
        "ModShiny.cs": """public class ModShiny : IModification
{
	public override bool HandleEvent(GetDisplayNameEvent E)
	{
		E.AddAdjective("{{Y|shiny}}", -20);
		E.AddAdjective(IComponent<GameObject>._S("Ctx", "dull"));
		return base.HandleEvent(E);
	}
}""",
        # a tag with a hole, a tag of holes alone, a with-clause, a title
        "Perched.cs": """public class Perched : Effect
{
	public override bool HandleEvent(GetDisplayNameEvent E)
	{
		E.AddTag("[{{B|perched on " + PerchedOn.an() + "}}]");
		E.AddTag("[{{B|" + Count + "}}]");
		E.AddWithClause("tail feathers");
		E.AddTitle("keeper of the Perch");
		return base.HandleEvent(E);
	}
}""",
        # an adjective a field holds, which a subclass sets
        "Glowing.cs": """public class Glowing : IPart
{
	public string Adjective = "glowing";

	public override bool HandleEvent(GetDisplayNameEvent E)
	{
		E.AddAdjective(Adjective);
		return true;
	}
}""",
        "Shimmering.cs": """public class Shimmering : Glowing
{
	public Shimmering()
	{
		Adjective = "shimmering";
	}
}""",
        # the event passes its parameter through: not a fragment of its own
        "GetDisplayNameEvent.cs": """public class GetDisplayNameEvent
{
	public void AddAdjective(string Adjective, int OrderAdjust = 0)
	{
		DB.AddAdjective(Adjective, OrderAdjust);
	}
}""",
    }

    def test_what_the_code_adds_to_a_name(self):
        with tempfile.TemporaryDirectory() as d:
            for rel, text in self.SOURCES.items():
                (pathlib.Path(d) / rel).write_text(text, encoding="utf-8")
            found = {e.key: e.where for e in codescan.scan_fragments(pathlib.Path(d))}
        self.assertEqual(set(found), {"{{Y|shiny}}", "[{{B|perched on {0}}}]", "tail feathers", "keeper of the Perch",
                                      "glowing", "shimmering"})
        self.assertEqual(found["tail feathers"], "Perched: те, з чим предмет («with …»)")


class HitMessage(unittest.TestCase):
    # a made-up attack in the shape of Combat's: a builder filled across if/else, handed to TakeDamage as its Message
    SOURCE = """public class Brawl : IPart
{
	public void Strike(bool Hard)
	{
		using TextBuilder sb = TextBuilder.Get();
		if (Attacker.IsPlayer())
		{
			sb.Append("{{g|You");
			if (Hard)
			{
				sb.Append(" hard");
			}
			sb.Append(" smack");
			if (!Terse)
			{
				sb.Append(" with ");
				Attacker.its_(Weapon, sb);
			}
			if (!Terse)
			{
				sb.Append('!');
			}
			sb.Append("}}");
		}
		else if (Defender.IsPlayer())
		{
			sb.Append("%T").Append(Attacker.GetVerb("smack")).Append(" you soundly");
		}
		E.SetParameter("Message", sb.ToString());
	}
}"""

    def test_every_path_once_and_the_same_condition_alike(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Brawl.cs").write_text(self.SOURCE, encoding="utf-8")
            found = {e.key for e in codescan.scan_text(pathlib.Path(d))}
        # «!Terse» decides both blocks at once: no «with» without «!», nor the other way round
        self.assertEqual(found, {"{{g|You hard smack with {0} {1}!}}", "{{g|You hard smack}}",
                                 "{{g|You smack with {0} {1}!}}", "{{g|You smack}}",
                                 "{0} smacks you soundly", "{0} smack you soundly"})


class RulesScan(unittest.TestCase):
    # made-up parts in the shapes the game's code takes
    SOURCES = {
        "ModGlinting.cs": """public class ModGlinting : IModification
{
	public override bool HandleEvent(GetShortDescriptionEvent E)
	{
		E.Postfix.AppendRules(GetDescription(Tier));
		E.Postfix.AppendRules(IComponent<GameObject>._S("Ctx", "Dull: no shine."));
		E.Postfix.AppendRules(delegate(StringBuilder sb)
		{
			sb.Append("Built by an action.");
		});
		return base.HandleEvent(E);
	}

	public static string GetDescription(int Tier)
	{
		return "Glinting: +" + Tier + " to shine.";
	}
}""",
        # a chain whose English only checks its localized twin: not a rule of its own
        "Checked.cs": """public class Checked : IPart
{
	public override bool HandleEvent(GetShortDescriptionEvent E)
	{
		E.Postfix.AppendRules(GetStats());
		return true;
	}

	public string GetStats()
	{
		using TextBuilder a = TextBuilder.Get();
		using TextBuilder b = TextBuilder.Get();
		a.Append("Shine cap: ").Append(Cap);
		IComponent<GameObject>._T("Ctx", "Shine cap: =cap=").SetArgument("cap", Cap).CompoundTo(b, "\\n");
		Strings.AssertLocalizationMatch(a.ToString(), b.ToString(), "Checked");
		return b.ToString();
	}
}""",
    }

    def test_rules_lines_the_code_writes(self):
        with tempfile.TemporaryDirectory() as d:
            for rel, text in self.SOURCES.items():
                (pathlib.Path(d) / rel).write_text(text, encoding="utf-8")
            found = {e.key for e in codescan.scan_rules(pathlib.Path(d))}
        self.assertEqual(found, {"Glinting: +{0} to shine."})

if __name__ == "__main__":
    unittest.main()
