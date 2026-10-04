"""Tables our C# code looks words up in: English text the game passes as it is (a creature's species), and the
English the Harmony patches catch (effect names and descriptions…). Their source is the game itself (sources.load
builds them from the Base folder and the decompiled code), so they go through the usual catalog, store and
translation, but the build writes them as C# (mod/Grammar/CodeTables.g.cs, not in git: its keys are the game's
English), not as a language file.

A catalog file is named Code.<Table>.example.xml; each entry is <entry Key="english" Text="▶english" Note="…" />.
A key may be a pattern: {0}, {1}… stand for what the code computes («-{0} DV»), and the translation must keep them.
Translator notes can add:
  uk-voc: <form>   the vocative too (table <Table>.voc), for texts that address someone
  uk-agree         the translation is a masculine adjective phrase that agrees with the object it describes
                   (table <Table>.agree): an effect «отруєний» shows as «отруєна» on a woman, «отруєні» on «ви»
"""
from __future__ import annotations

import pathlib
import re
import xml.etree.ElementTree as ET

from .units import MARK, uncommented

PREFIX = "Code."
SPECIES = "Code.Species.example.xml"
EFFECTS = "Code.Effects.example.xml"
VOCATIVE = re.compile(r"^uk-voc:\s*(.+?)\s*$")
AGREE = re.compile(r"^uk-agree\b")


def is_code_table(name: str) -> bool:
    return name.startswith(PREFIX)


def table_name(name: str) -> str:
    """«Code.Species.example.xml» → «Species»."""
    return name[len(PREFIX):].removesuffix(".example.xml")


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "&#10;").replace("\t", "&#9;"))


def table_xml(table: str, entries: list[tuple], build: str | None, source: str, attr: str = "Text") -> str | None:
    """The string table for a code table, an entry per (key, note) or (key, English for the translator, note): the
    key is what the patch looks up, the English what the translator reads (by default the key itself). attr names
    the translated attribute: «Forms» for a table whose entries are verb forms (checks.py knows it by that)."""
    if not entries:
        return None
    rows = [(e[0], e[0], e[1]) if len(e) == 2 else e for e in entries]
    body = "".join(f'  <entry Key="{_esc(k)}" {attr}="{MARK}{_esc(text)}"' + (f' Note="{_esc(n)}"' if n else "")
                   + " />\n" for k, text, n in rows)
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!--\n'
            f"Caves of Qud - Generated Localizable XML {build or 'unknown'}\n"
            f"Not from the game: tools/qudtr/codetables.py builds it from {source}.\n\n"
            f'<codetable Name="Key">\n\n  <entry Key="Key" {attr}="DisplayText">\n\n-->\n'
            f'<codetable Name="{table}" Lang="example" Encoding="utf-8">\n{body}</codetable>\n')


SPECIES_TAG = re.compile(r'<(?:tag|property)\s+Name="Species"\s+Value="([^"]+)"')
GENOTYPE_SPECIES = re.compile(r'<genotype\b[^>]*\bSpecies="([^"]+)"')


def species_xml(blueprints: dict[str, str], genotypes: str | None, build: str | None) -> str | None:
    """Every species the game can print through =x.species= / =x.apparentSpecies= (GameObject.GetSpecies: the
    Species property or tag; the genotypes' Species)."""
    keys = set()
    for text in blueprints.values():
        keys.update(SPECIES_TAG.findall(uncommented(text)))
    if genotypes:
        keys.update(GENOTYPE_SPECIES.findall(uncommented(genotypes)))
    keys = sorted(k for k in keys if re.search(r"[A-Za-z]", k))  # not the "*" wildcard
    return table_xml("Species", [(k, None) for k in keys], build,
                     "the Species tags of Base/ObjectBlueprints and Base/Genotypes.xml")


EFFECTS_NOTE = ("Ефект: {where}. Назва ефекту (DisplayName) або рядок його опису; {{0}}… — те, що рахує код (числа, "
                "імена), лишіть їх; слово при числі рахуйте ним: {{0}} {{0:хід:ходи:ходів}}. Назва-прикметник, що описує носія («poisoned»), — у чоловічому роді з нотаткою "
                "uk-agree: мод узгодить її з носієм («отруєна», для гравця — «отруєні»).")


def effects_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """Effect names and descriptions the game's C# writes (codescan.scan_effects)."""
    from . import codescan
    entries = [(e.key, EFFECTS_NOTE.format(where=e.where)) for e in codescan.scan_effects(decompiled)]
    return table_xml("Effects", entries, build, "the decompiled game code (XRL.World.Effects)")


DIDX = "Code.DidX.example.xml"
DIDX_NOTE = ("Розповідь гри (DidX, {where}). <subject> — хто діє, <object> і <indirect> — над чим і з чим. Перекладіть "
             "шаблоном нашої граматики: =subject.Name= =subject.v:…:…:…=, =object.name=, =indirect.name=, "
             "=object.p:…:…= тощо (docs/grammar.md); кінцевий знак — як в оригіналі. {{0}}… — те, що рахує код: "
             "лишіть його (слово при числі рахуйте ним: {{0}} {{0:хід:ходи:ходів}}) або, якщо це англійський "
             "займенник («its»), приберіть і поставте нотатку «qud-ok: code-hole — займенник». <verb> — дієслово з "
             "даних гри (снаряд, пристрій): на його місці поставте {{v}}, мод підставить його форму з таблиці Verbs "
             "(«=subject.Name= {{v}} повз =object.p:вас:ціль (@)=!»).")


def didx_xml(decompiled: pathlib.Path, build: str | None, blueprints: dict[str, str] | None = None) -> str | None:
    """The narration the game conjugates itself (codescan.scan_didx)."""
    from . import codescan
    rows = [(key, english, DIDX_NOTE.format(where=where))
            for key, english, where in codescan.scan_didx(decompiled, blueprints)]
    return table_xml("DidX", rows, build, "the decompiled game code (Messaging.XDidY and its wrappers)")


VERBS = "Code.Verbs.example.xml"
VERBS_NOTE = ("Дієслово з даних гри ({where}): так звучить снаряд, пристрій, істота. Дайте три форми, як для "
              "=X.v:…=: він/вона — ви — вони, через двокрапку: «свистить:свистите:свистять». Фразу — цілком: "
              "«розсипається на порох:розсипаєтеся на порох:розсипаються на порох». Мод ставить їх на місце {{v}} у "
              "розповіді (Code.DidX) і в =verb|uk.v#subject= (Strings).")


def verbs_xml(decompiled: pathlib.Path, build: str | None, blueprints: dict[str, str] | None = None) -> str | None:
    """The verbs the narration takes from the game's data (codescan.scan_verbs)."""
    from . import codescan
    entries = [(e.key, VERBS_NOTE.format(where=e.where)) for e in codescan.scan_verbs(decompiled, blueprints)]
    return table_xml("Verbs", entries, build, "the decompiled game code and Base/ObjectBlueprints (data verbs)",
                     attr="Forms")


TEXT = "Code.Text.example.xml"
TEXT_NOTE = ("Текст, який пише сам C# гри ({where}): спливне вікно, відмова, рядок журналу повідомлень чи "
             "журналу пригод. Один рядок; {{0}}… — те, що рахує код (імена, числа), лишіть їх, а слово при числі "
             "рахуйте ним: {{0}} {{0:хід:ходи:ходів}} (англійський займенник можна прибрати з нотаткою "
             "«qud-ok: code-hole — займенник»). Безглуздий ключ, складений з кусників коду, "
             "лишайте без перекладу.")


def text_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """Popups, failure messages and message-log lines the game's C# writes (codescan.scan_text)."""
    from . import codescan
    entries = [(e.key, TEXT_NOTE.format(where=e.where)) for e in codescan.scan_text(decompiled)]
    return table_xml("Text", entries, build, "the decompiled game code (popups, Fail, the message log, the journal)")


WORDS = "Code.Words.example.xml"
WORDS_NOTE = ("Коротка назва з коду гри ({where}). Гра показує її як є або вставляє в речення на місце {{0}}, "
              "тож перекладіть як назву в називному відмінку, з малої літери, якщо так в оригіналі.")


def words_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """Names the code keeps in constants: journal tabs, stances, breaths (codescan.scan_words)."""
    from . import codescan
    entries = [(e.key, WORDS_NOTE.format(where=e.where)) for e in codescan.scan_words(decompiled)]
    return table_xml("Words", entries, build, "the decompiled game code (constants the player reads)")


ABILITIES = "Code.Abilities.example.xml"
ABILITIES_NOTE = ("Активна здібність ({where}): так її називають панель здібностей, список здібностей і спливні "
                  "вікна. Англійське дієслово — інфінітив («Spit Acid» → «Плюнути кислотою»), англійський іменник — "
                  "іменник («Telekinesis» → «Телекінез»), як у вже перекладених назвах здібностей у Strings. Опис "
                  "перекладайте реченням; {{0}}… — те, що підставляє код (назва міни, число), лишіть їх.")


def abilities_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """The names and descriptions the code gives activated abilities (codescan.scan_abilities)."""
    from . import codescan
    entries = [(e.key, ABILITIES_NOTE.format(where=e.where)) for e in codescan.scan_abilities(decompiled)]
    return table_xml("Abilities", entries, build, "the decompiled game code (activated abilities)")


FRAGMENTS = "Code.Fragments.example.xml"
FRAGMENTS_NOTE = ("Частина назви, яку дописує код ({where}). Прикметник перед назвою — у чоловічому роді, мод "
                  "узгодить його з назвою («відточений» → «відточена сокира»; неправильні форми — нотатка "
                  "«uk-forms: ж|с|мн»). Позначка в дужках після назви — безособово, як «[зламано]», «[порожньо]». "
                  "«з …» — в орудному відмінку («редуктором»). Розмітку {{{{X|…}}}} лишайте, {{0}} — те, що підставляє "
                  "код (назва, число).")


def fragments_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """What the code adds to an object's name: adjectives, tags, clauses, titles (codescan.scan_fragments)."""
    from . import codescan
    entries = [(e.key, FRAGMENTS_NOTE.format(where=e.where)) for e in codescan.scan_fragments(decompiled)]
    return table_xml("Fragments", entries, build, "the decompiled game code (parts of object names)")


RULES = "Code.Rules.example.xml"
RULES_NOTE = ("Правило в описі предмета чи істоти ({where}): рядок {{{{rules|…}}}} під описом. Перекладайте "
              "реченням у стилі вже перекладених правил («Гострий: +1 до кидків пробиття»); {{0}}… — числа й "
              "назви, які підставляє код, а слово при числі рахуйте ним: {{0}} {{0:хід:ходи:ходів}}. Англійські "
              "займенники й дієслова-пропуски («This item»/«These items», «has»/«have») можна прибрати з нотаткою "
              "«qud-ok: code-hole — …».")


def rules_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """The rules lines the code writes into descriptions (codescan.scan_rules)."""
    from . import codescan
    entries = [(e.key, RULES_NOTE.format(where=e.where)) for e in codescan.scan_rules(decompiled)]
    return table_xml("Rules", entries, build, "the decompiled game code (rules lines of descriptions)")


DAMAGE = "Code.Damage.example.xml"
DAMAGE_NOTE = ("Кінець рядка шкоди ({where}): після «Ви отримуєте 5 шкоди» чи «Пащеклац отримує 5 шкоди». %t, %o — "
               "чиє це було, %O — хто це зробив, %S — хто розпалив: замість них пишіть "
               "=object.p:<гравець>:<інший, @ — ім’я>:<коли нікого>=, напр. «від =object.p:вашого укусу:укусу (@):"
               "укусу=.»; =subject…= — той, хто отримує шкоду. Ім’я в пропуску чи @ стоїть у називному, тож — у "
               "дужках. {{0}}… — те, що підставляє код.")


def damage_xml(decompiled: pathlib.Path, build: str | None) -> str | None:
    """The tails of the damage lines (codescan.scan_damage): mod/Patches/DamagePatches renders them."""
    from . import codescan
    entries = [(e.key, DAMAGE_NOTE.format(where=e.where)) for e in codescan.scan_damage(decompiled)]
    return table_xml("Damage", entries, build, "the decompiled game code (TakeDamage messages)")


KEY_IN_CONTEXT = re.compile(r"^entry\[Key=(.*)\]@(?:Text|Forms)$", re.S)


def key_of(msgctxt: str, msgid: str) -> str:
    """The key of a code-table unit: its context names it; the English is only for the translator."""
    m = KEY_IN_CONTEXT.match(msgctxt or "")
    return m.group(1) if m else msgid


def entries(xml_text: str) -> list[str]:
    return [e.get("Key") for e in ET.fromstring(xml_text).iter("entry")]


def code_tables_cs(tables: dict[str, dict[str, str]]) -> str:
    """The C# that fills CodeTables (mod/Grammar/CodeTables.cs): table → English → Ukrainian."""
    def lit(s: str) -> str:
        return ('"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
                .replace("\t", "\\t").replace("\0", "\\0") + '"')
    blocks = []
    for name, table in sorted(tables.items()):
        lines = "".join(f"                [{lit(k)}] = {lit(v)},\n" for k, v in sorted(table.items()))
        blocks.append(f"            t[{lit(name)}] = new Dictionary<string, string>\n            {{\n{lines}            }};\n")
    return ("// <auto-generated> by `py tools/qud.py build` from the Code.* catalogs. Not in git: the keys are the\n"
            "// game's English.\n"
            "using System.Collections.Generic;\n\n"
            "namespace CavesOfQudUA.Grammar\n{\n"
            "    public static partial class CodeTables\n    {\n"
            "        static partial void Fill(Dictionary<string, Dictionary<string, string>> t)\n        {\n"
            + "".join(blocks) + "        }\n    }\n}\n")
