# Чернетка для Freehold: де локалізації бракує шва

Технічний звіт англійською для Freehold Games (план, етап 5: «Звіт Freehold про місця, де „не вистачає
шва“»). Mike вирішує, чи надсилати його, і як: з листом D7 чи окремо (Discord `#modding`). Дані зібрано з
декомпільованої збірки **2.0.212.31** і з наших ігор 2026-10-02 і 2026-10-04. Цитати гри — лише ідентифікатори
й короткі рядки для пояснення.

---

## Ukrainian translation of Caves of Qud: places where the localization framework has no seam yet

We are translating Caves of Qud into Ukrainian on the `lang-experimental` branch (2.0.212.31) with the
official framework: string tables, a `Translator` provider of our own for the grammar, and Harmony patches
where neither reaches. 99.5% of the string table units are translated. The places below are where English
still reaches a Ukrainian player, or where we had to patch game methods to get past it. Each one says
where it is in the code, what the player sees, and what would let a translation handle it without a patch.

### Text the code builds in English

1. **Lines under an ability's description** (`Templates.StatCollector`). `AddChangePostfix`,
   `AddPercentChangePostfix`, `AddComputePowerPostfix` and `CollectCooldownTurns` append interpolated
   English: `$"\n{what} increased by {change} due to {dueTo}."`, `"Cooldown reduced by {n} due to {reason}."`,
   `"Cooldown cannot be reduced below " + n + " rounds."`. The callers pass `what` and `dueTo` as literals
   ("Damage", "Knockdown save", "high strength", "compute power"). A player sees «Cooldown reduced by 5 due
   to Сила волі: висока.» under almost every ability. *Suggestion:* `_T` templates with `what`, `dueTo` and
   the number as arguments, and `what`/`dueTo` from the string tables.
2. **Statistic values set as English text** (`StatCollector.Set`): `"Strength " + (SlamSave + num)`
   (Shield_Slam), `"sight"`, `"none"`, `"once per night"`, `"Strength / Agility vs. character level"`.
   They show on `statline` nodes: «Кидок проти падіння: Strength 21». *Suggestion:* a localized value, or a
   statistic ID that the template renders through its title.
3. **The system menu** (`XRLCore`, `CmdSystemMenu`): `new string[5] { "Control Mapping", "Options",
   "Game Info", "Save and Quit", text }` — only the last option goes through `_S`. The same holds for the
   checkpoint options and «End Test».
4. **Option lists and intros built in place** for `Popup.PickOption`: the companion follow distance
   (`"Instruct " + E.Item.t() + " to follow at what distance?"`, `"close"`, `"medium"`, `"far"`), the rename
   menu (`"Enter a name for " + text + "."`, `"Choose a random name from " + … + " culture."`), the mod
   configuration prompt («These mods are {{red|disabled}} in the save:»), the Spindle negotiation intros.
5. **The «Game Info» popup** (`XRLCore`, `ShowBlockWithCopy`): `GameMode + " mode."` and
   `"Turn " + Turns` are English, and `GameMode` is the raw ID.
6. **Verbs joined to names**: `GameObject.Does(verb)` and `GetVerb(verb)` conjugate English verbs and glue
   them to a (translated) display name; there are 217 `Does("…")` calls, 61 of them `Does("are")`. Any
   sentence built that way stays half English, and for a language with gendered past tense no key can
   cover it. *Suggestion:* move these messages to `_T` templates with `=subject.…=` variables, as
   `DidX`/`XDidY` already do through `Messaging`.

### Names a save keeps in the language it was made in

7. **Body parts** (`BodyPart.WriteValues`/`ReadValues`): `Name` and `Description` are stored as text at
   creation. A character made before a language (or a translation of `Bodies`) was installed keeps «Left
   Hand», «Worn on Back» in the equipment screen. *Suggestion:* derive the shown name from the part's type
   and laterality at display time, or store the type only.
8. **Activated abilities** (`ActivatedAbilityEntry.Write`/`Read`): `DisplayName` and `Description` are
   stored text; 50 `AddMyActivatedAbility("…")` calls pass English literals («Intimidate», «Clone [3
   left]»), not table entries. *Suggestion:* string-table names, resolved when shown.

### Places that skip the display name

9. **Required powers in the skills list** (`SPNode.ModernUIText`): `argument = Entry.Name;` — the English
   name — where the exclusion right below uses `Entry2.GetDisplayName()`. A Ukrainian player reads «Draw a
   Bead» among Ukrainian power names. *Suggestion:* `GetDisplayName()` there too.
10. **A save's game mode on the load screen** (`SavesAPI`, «QudAPISaves InfoDescription»): the argument
    `gamemode` is `json.GameMode`, the mode's ID («Classic», «Roleplay»), not its title from
    `EmbarkModules`.
11. **The inventory filter's «ALL» button**: `FilterBarCategoryButton.categoryTextMap = { "*All": "ALL" }`
    is a literal, and the category lookup for `*All` (`Physics (Inventory) Category`) logs a string
    table miss.
12. **Prefab labels**: «delete» and «Mods Differ» in `SaveManagementRow`, and the scene headers we saw on
    the character screen («SECONDARY ATTRIBUTES», «RESISTANCES»), are prefab text with no table entry. The
    scene file has four more that no code sets, which look like the world generation screen's eons
    («COSMOLOGIC», «GEOLOGIC», «DEEP HISTORIC», «NEAR HISTORIC»).

### Small issues, English included

13. **A stray comma in skill requirements** (`PowerEntryRequirement.Render`): `if (i > 0) sb.Append(", ")`
    runs before the elements are joined by `=elements.join=`, which separates them again. The line reads
    «[300sp] , 29 Strength, 23 Agility or , 29 Agility, 23 Strength» in English too.
14. **Lookups before the mods load**: `MessageLogWindow.Init` sets the log's title once, before the
    language mods are loaded, so it stays «Message log» (we set it again in `GameInit`); the
    `DifficultyEvaluation` labels are looked up as early, which only logs misses.
15. **A mutation's rank is set twice** (`CharacterStatusScreen.HandleHighlightMutation`): from the table
    («CharacterStatusScreen MutationRankText») and on the next line again as `$"{{{{G|RANK {…}/10}}}}"`, so
    the translated rank never shows.
16. **A doubled verb in a missile hit** (`MissileWeapon`): `Projectile.Does("hit", …) + Projectile.GetVerb("hit")`
    reads «… hits hits …» in English too.
17. **Hit points lost** (`GameObject`, stat penalty): `Does("lose") + num + " hit " + …` gets a negative `num`
    and no space before it: «You lose-5 hit points.».

### From our research before the playtests

18. The Factions export writes the water ritual's dish question as `recipetext`, while the faction loader
    reads `RecipeText`, so its translation is ignored; the export also leaves out the interests'
    `BuyDescription` and the factions' `DefaultAddress`.
19. `[DisplayText]` is missing on 21 part classes whose text is shown.
20. `Bodies`, `Commands`, `Genders` and `Colors` have no export; we build tables for them from the game's
    own XML.
21. `VariantName` and other tags that are shown to the player are not in the export.
22. Ability and effect names come from code rather than from the tables.
23. `Grammar.MakePossessive`, `Pluralize` and `MakeTitleCase` apply English rules to any text; a call
    through the `Translator` provider would let a language opt out.

Everything above is something we can patch or work around, and mostly already have. We list it so that
the framework can carry these places itself, and so that other translations meet them less. Thank you
for the framework: the string tables and the provider carried almost the whole game.
