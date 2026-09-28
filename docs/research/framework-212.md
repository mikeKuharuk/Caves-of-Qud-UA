# Фреймворк локалізації зсередини (2.0.212.31) і перевірка в грі

Зібрано 2026-09-28 на гілці `lang-experimental`, збірка **2.0.212.31** (Steam buildid 25473993,
MarketingVersion 1.1.x, «1.1.0 Lang Beta» у кутку екрана). Код:
`work/decompiled/2.0.212.31/Assembly-CSharp/` (не в git). Позначки, як і скрізь:
**[перевірено]**, **[за звітом]**, **[припущення]**.

## Точки розширення для української (у коді)

### Провайдер мови: `[LanguageProvider("uk")]` **[перевірено]**

- `XRL.Language.LanguageLoader.LoadLanguages()` перебирає всі типи з модів. Клас, позначений
  `[LanguageProvider(<код>)]`, з кодом, що збігається з активною мовою, стає провайдером
  (`Translator.SetProvider`). В англійської це `TranslatorEnglish : TranslatorBase`.
- `Translator.Provider` (абстрактний клас) — офіційне місце для граматики мови. Перевизначається:
  - Перенос рядків і ширина: `NextPossibleLineBreakIndex`, `GetGraphemeWidth`. В англійській
    CJK-символи мають ширину 1.5, решта — 1.
  - Списки: `MakeAndList`, `MakeOrList`, `MakeCommaList`.
  - Артиклі: `DefiniteArticle`, `IndefiniteArticle`, `AddArticle`, `ExtractArticle`. Українською
    всі вони мають повертати порожнечу.
  - Числа словами: `Cardinal`, `CardinalNo`, `Ordinal`, `OrdinalWithDigits`, `Multiplicative`.
  - **Назви об'єктів:** `GameObjectDisplayName` і `CreateDescriptionBuilder` — власний
    `DescriptionBuilder`, у якому можна узгоджувати прикметники.
  - Назви зон з біомами: `MutateZoneName`.
  - Регістр і культура: `GetCultureInfo` (uk-UA), `ToLower`/`ToUpper`, компаратори рядків,
    `IsWordCharacter`.
  - Спотворення тексту: `Stutterize`, `Weirdify`/`Unweirdify`.
- **Чого провайдер не покриває:** множини (`Grammar.Pluralize`), дієслів (`ThirdPerson`) і
  займенникових відмінків. Це саме ті скарги Pirogov. Тут потрібні власні replacers
  (див. нижче) або Harmony.

### Replacers тільки для своєї мови **[перевірено]**

- У `HasVariableReplacerAttribute` з'явилося поле `Lang`. `VariableReplacers.YieldMethods`
  бере методи з класу з `Lang = null` (для всіх) або з `Lang == ActiveLanguage`.
- Отже, `[HasVariableReplacer(Lang = "uk")]` із `[VariableReplacer(..., Override = true)]` підмінить
  англійські `=subject.T=`, `=verb:…=`, `=pronouns.…=` лише тоді, коли гра працює українською.
- Wish `testlangreplacers` показує replacers лише активної мови, `testreplacers` — усі.

### Умовні теки й файли за мовою **[перевірено]**

- `manifest.json` → `Directories[].Languages` (синоніми `Language`, `Lang`): тека вантажиться
  лише для перелічених мов. Годиться для C#-коду: англомовні гравці його навіть не компілюватимуть.
  Коли саме обчислюється `ActiveLanguage` під час завантаження модів, **ще не перевірено**:
  до `GameManager.Playing` він повертає `"en"`.
- XML з `Lang="…"` на корені вантажиться лише для цієї мови й отримує пріоритет -1000, якщо
  `LoadPriority` не задано (`DataManager.CacheFile`).
- JSON: `DataManager.FilePathFromBasePreferModFile` спершу шукає в модах `<ім'я>.<мова>.json`.
  Тож `HistorySpice.uk.json` підхопиться автоматично. У `HistoricSpice` є ще ключ `"lang"`.

### Таблиця рядків **[перевірено]**

- `XRL.Language.Strings._S(Context, ID)` / `_T(...)` (шаблон → `ReplaceBuilder`). Пошук іде
  спершу за Context+ID, потім лише за ID (`StringsLoader.ContextStrings(null)`).
- Кожен запис із Context **також** потрапляє в загальну таблицю за ID (`Strings.TryAdd`). Тому
  переклад рядка з одним Context може «просочитися» в інше місце з тим самим ID і невідомим
  Context. Наприклад, наш «Help → Довідка» з'явився й у підказці `[F1]` в налаштуваннях.
- `OrderAdjust` в `<string>` дозволяє перекладу змінити порядок елементів
  (`_S(Context, ID, DefaultOrder, out Order)`). Це один зі способів боротися з фіксованим
  порядком слів.
- Якщо переклад не знайдено, повертається ID, тобто англійський текст.

### Шрифти **[перевірено в коді]**

- `<lang Code DisplayName FontFamily>`: мова може задати сімейство шрифту (`LanguageData.FontFamily`).
  Типово це `FontManager.GetDefaultFontFamily()`.
- `FontManager.UpdateFontFallbacks()` прибирає з `TMP_Settings.fallbackFontAssets` усі «Source
  Han*» і додає один: той, що заданий мовою, або **`Source Han Mono SC`**. Саме з нього беруться
  гліфи, яких немає в основному шрифті елемента.

### Консоль (класичний UI, карта) **[перевірено в коді й у грі]**

- `GameManager`: символ спершу переводиться в CP437 (`AsCP437()`). Якщо код > 255, клітинка
  отримує **TMP-«імпостер»** `Prefabs/Imposters/TMPTileImposter` з цим символом і кольорами, а
  бітмап-гліф стає пробілом. На 2.0.211 такі символи просто зникали.

## Перевірка в грі (2026-09-28) **[перевірено]**

| Що перевіряли | Результат |
|---|---|
| Мод вантажиться, тека `Language/` за умовою `Build >= 2.0.212` | ✅ `build_log.txt`: `Loading path: Language\`, символи `VERSION_1_1`, `BUILD_2_0_212`, `MOD_CAVESOFQUDUA` |
| «Українська» в меню мов (`Languages.xml`) | ✅ Зміна мови перезапускає процес гри (новий PID) |
| Головне меню (`Strings.uk.xml`) | ✅ Усі пункти українською. `Мова (=currentLanguage=)` показує **код** `uk`, а не назву |
| Довідка «Швидкий старт» (`Manual.uk.xml`) | ✅ Текст, кольори `{{W|…}}`, `{{hotkey|…}}`, `{{?KB|…}}`, клавіші `~Cmd…` працюють. `DisplayName` теми не працює: лишається QUICKSTART, як і попереджає вікі |
| Злиття blueprint-а (`Creatures.uk.xml`) | ✅ Кіт показується як «Ктесіф» у швидкому огляді, в огляді й у класичному UI. Опис англійський, бо ми його не перекладали |
| Змішана мова | ✅ Неперекладене лишається англійським, наприклад теми довідки після Quickstart |
| Кирилиця в сучасному UI | ✅ Усі 33 літери, зокрема Ґґ Єє Іі Її; `’ ʼ '`, `« »`, `—`, `№` |
| Метрики шрифту | ⚠️ Див. нижче |
| Кирилиця в класичному UI (консоль) | ✅ з вадою: літери малюються TMP-імпостерами, дрібніші й тонші за бітмап-шрифт, по одній у клітинці, тож слово виглядає розрідженим («К т е с і ф») |
| Назви клавіш | ℹ️ Гра показує клавіші за **розкладкою ОС**. З українською розкладкою `L` → «Д», `W` → «Ц» |
| `OptionDebugStringTableMisses` | ✅ Пише `String table miss - Lang uk - Context="…" ID="…"` у `Player.log`. На старті ~5.1 тис. промахів (діалоги резолвляться під час завантаження), за меню, створення світу й перші хвилини гри — ще ~700 (здебільшого історія світу: `HistoricEvent`, `Resheph`, `VillageHistory`) |
| `OptionDebugStringTableLoadingChecks` | ✅ Запобіжник спрацював на **навмисно** хибних записах: невідомий ID → «doesn't seem to be defined», чужий Context → «exists, but not in this context». На правильних записах попереджень немає |

### Метрики шрифту: що саме виміряно

- **Моноширинні екрани** (довідка, повідомлення) рендерять кирилицю тим самим моноширинним
  шрифтом, що й латиницю. Вигляд рівний.
- **Пропорційний шрифт** (ліве меню на титульному екрані): кирилиця береться з **іншого,
  моноширинного** шрифту. Тест із десятьма однаковими за формою літерами:
  - `ММММММММММ` вужчі за латинські `MMMMMMMMMM`;
  - `аааааааааа` ширші за `aaaaaaaaaa`;
  - `оооооооооо` мають ту саму ширину, що й `oooooooooo`;
  - усі кириличні рядки однакової довжини, тобто гліфи моноширинні (fallback).
- Довгий рядок у цьому меню **обрізався праворуч**, а не переносився: зникли `Рр Сс Тт Уу` і
  `№1`. Висновок: пункти меню мають фіксовану ширину, а перенос рахує символи, а не пікселі.
- Що робити (етап 7):
  - визначити, які TMP-ассети використовують пропорційні елементи;
  - додати шрифт із кирилицею тієї ж гарнітури або задати свій `FontFamily`;
  - чи потрібне перевизначення `GetGraphemeWidth`, **не перевірено**.

## Як відтворити

1. `powershell -File tools/deploy.ps1` (junction `Mods\CavesOfQudUA` → `mod/`).
2. Запустити гру через Steam (`steam://rungameid/333640`). Мова → «Українська».
3. Опції → Debug → «Show Debug (Translation) options» (потрібні «Show advanced options»), далі
   «Log string table lookup misses…» і «Enable extra strings xml loading checks». Опції
   зберігаються в `…\CavesOfQud\Local\PlayerOptions.json`.
4. Для швидкого старту: Debug → «Show quickstart option during character creation».
5. Промахи: `py tools/misses.py` (або з аргументами — збережені логи з `work/logs/`).
