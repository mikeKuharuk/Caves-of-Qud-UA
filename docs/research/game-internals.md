# Як Caves of Qud працює з текстом: перевірені факти (основна гілка 2.0.211)

Зібрано 2026-09-28 на локальній інсталяції гри. Усе нижче **виміряно** в декомпільованому коді
(`work/decompiled/`, не в git) або у файлах гри, якщо прямо не позначено інше. Шляхи до файлів
коду вказані відносно `work/decompiled/2.0.211.56/Assembly-CSharp/`.

> **Важливо.** Це аналіз **основної** гілки 2.0.211, тепер лише для довідки. Переклад будується
> на `lang-experimental` (2.0.212.x). Що там змінилося і що перевірено в грі — у
> `framework-212.md`. Коротко про розбіжності з цим документом:
> - кирилиця в консолі на 212 видима завдяки TMP-імпостерам;
> - для граматики є `[LanguageProvider]` і replacers за мовою;
> - мод-XML читається як UTF-8, якщо на корені стоїть `Encoding="utf-8"`.

## Версія, яку ми досліджували

| Що | Значення |
|---|---|
| Гра | Caves of Qud, Steam app 333640, buildid 25520692 |
| Версія збірки (`Assembly-CSharp.dll`) | **2.0.211.56** |
| Рушій | Unity **6000.0.77f1** (Mono, не IL2CPP, тому код можна декомпілювати й патчити) |
| Розташування гри | `D:\Steam\steamapps\common\Caves of Qud` |
| Дані користувача / моди | `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud` (тека `Mods` створюється вручну) |

У `CoQ_Data/Managed/` є все потрібне для модів: `0Harmony.dll` (Harmony), `RoslynCSharp*.dll` і
`Microsoft.CodeAnalysis*.dll` (гра сама компілює `.cs` файли модів), `Newtonsoft.Json.dll`,
`Unity.TextMeshPro.dll`. Поруч лежить `Assembly-CSharp.xml` з XML-документацією до частини API.

Офіційного механізму локалізації в коді **немає**: жодних типів `Localization`/`Translation`,
жодної опції мови в `Options.xml`. `UnityEngine.LocalizationModule.dll` є стандартним модулем
Unity, а не пакетом Localization. На 2.0.212 фреймворк уже є, див. `official-framework.md`.

## Де лежить текст і скільки його

Приблизний підрахунок скриптами з `tools/analysis/`. Рахуються слова англійського тексту без
розмітки. Службові ідентифікатори відфільтровано.

| Джерело | Слів | Примітка |
|---|---:|---|
| `ObjectBlueprints/*.xml` → `part[Description].Short` | ~55 000 | 2298 описів істот і предметів |
| `ObjectBlueprints/*.xml` → `part[Render].DisplayName` | ~5 500 | 2136 назв |
| `Conversations.xml` + `HiddenConversations.xml` (`<text>`, `<choice>`, `<node>`) | ~67 000 | діалоги |
| `Books.xml` (`<page>`) | ~24 000 | серед них вірші, стилізовані під середньоанглійську |
| `HistorySpice.json` | ~16 500 | граматика процедурної історії (султани, села, міфи) |
| Інші XML (Skills, ActivatedAbilities, Manual, Options, Commands, Quests, Factions, Mutations, EmbarkModules, Bodies, Worlds, Mods…) | ~20 000 | |
| **Разом дані** | **≈190 000** | |
| Рядкові літерали в `Assembly-CSharp.dll` (`ldstr`, схожі на прозу) | ≤81 000 | 14 163 місця виклику; частина з них налагодження та логи |
| `LibraryCorpus.json` (+ `.raw.txt`, `Corpus/*.txt`) | ~354 000 | корпус для марковських ланцюгів, з якого генеруються книги. Дослівно не перекладається, див. нижче |

Лише ~8% текстових полів XML містять змінні `=...=`. Здебільшого це займенники
(`=pronouns.possessive=` 616 разів, `=pronouns.subjective=` 230), `=name=`, `=verb:...=`. Решта
XML-тексту статична, тож це найпростіша частина роботи.

## Завантаження модів (перевірено в коді)

- Мод — це тека в `Mods/` з `manifest.json` (`XRL/ModManifest.cs`). Поля маніфесту: `ID`,
  `LoadOrder`, `Title`, `Description`, `Tags`, `Version`, `Author`, `PreviewImage`,
  `Directories`, `Dependencies`, `LoadBefore`, `LoadAfter`. `config.json` застарів і дає
  попередження.
- `Directories` (`XRL/ModDirectory.cs`) підключає підтеки за умовами: `Version` (маркетингова
  версія гри), `Build` (версія ядра), `Options` (стан опцій), `Dependencies`, `Exclusions`.
  Так можна тримати переклади під кілька версій гри або вмикати частини перекладу опціями.
- Типи файлів (`XRL/ModFile.cs`): `.xml`, `.json`, `.cs` (компілюється в грі), `.png`
  (спрайти), `.wav/.ogg/.aiff/.mp3`, `.dll` (готові збірки), `.rpm` (мапи).
- XML-файли групуються **за назвою кореневого елемента**, а не за назвою файлу
  (`XRL/DataManager.cs`, `CacheFile`). Атрибут `LoadPriority` на корені задає порядок.
- Під час читання XML `XmlDataHelper` проганяє атрибути й текстові вузли через
  `Sidebar.ToCP437()`, тобто перетворює Unicode-символи CP437 на коди 0–255
  (`XRL/XmlDataHelper.cs`, `GetAttribute`/`GetTextNode`). Кирилиці це не стосується.

### Семантика злиття, яка дозволяє перекладати без копіювання цілих об'єктів

- **ObjectBlueprints**: `<object Name="X" Load="Merge">` (або `MergeIfExists`) зливає частини
  за `Name`, а атрибути частини зливаються **поштучно** (`ObjectBlueprintXMLChildNode.Merge`).
  Тому достатньо такого:
  ```xml
  <objects>
    <object Name="Snapjaw" Load="Merge">
      <part Name="Render" DisplayName="…" />
      <part Name="Description" Short="…" />
    </object>
  </objects>
  ```
- **Conversations**: за замовчуванням діє `Merge` (`ConversationLoader.cs`,
  `ConversationXMLBlueprint.Merge`). Дочірні елементи зіставляються за (тип елемента, `ID`,
  `Cardinal`); `Cardinal` означає порядковий номер серед однакових. Непорожній `Text` замінює
  текст, атрибути зливаються. `Load="Replace|Add|Remove"` змінює поведінку.
- Решта завантажувачів (Books, Quests, Skills, Options…) ще **не перевірена**. У кожного своя
  семантика, і це треба дослідити, перш ніж генерувати для них файли.

## Моди на C#

- Методи з атрибутами збираються зі **всіх збірок модів** через
  `ModManager.GetMethodsWithAttribute(...)`.
- Система змінних `=subject.T=`, `=pronouns.possessive=` тощо живе в
  `XRL.World.Text.Delegates/VariableReplacers.cs`. Замінники реєструються атрибутами
  `[VariableReplacer]`, `[VariableObjectReplacer]` і `[VariablePostProcessor]` на класі з
  `[HasVariableReplacer]`. В атрибута є прапорець **`Override`**, тож мод може **перевизначити
  наявні** замінники (займенники, артиклі, дієслова) українськими версіями й **додати нові**,
  наприклад з відмінком. Це головна точка розширення для української граматики.
- `XRL.Language.Grammar` жорстко зашитий під англійську: `A`/`IndefiniteArticle`, `Pluralize`
  із таблицями винятків, `ThirdPerson`, `MakePossessive`, `MakeAndList`/`MakeOrList`,
  `Cardinal`/`Ordinal`, `MakeTitleCase`. Усе це доведеться перехоплювати Harmony-патчами.
- Назва предмета чи істоти збирається в `XRL.World.DescriptionBuilder` з частин: основа
  (`ORDER_BASE`), прикметники (`ORDER_ADJECTIVE = -500`), підрядні звороти («of fire»,
  `ORDER_CLAUSE = 600`), теги (`[empty]`), мітки, почесні титули, епітети. Українською
  прикметники мусять узгоджуватися з родом, числом і відмінком основи. Це окрема задача.
- Типовий захардкоджений текст виглядає так:
  `Popup.ShowFail("A loud buzz is emitted. The failure glyph flashes on the side of " + ParentObject.t() + ".")`.
  Рядок складено конкатенацією з англійськими артиклями (`t()` дає «the X»).
  Найбільше таких рядків у `XRL.World.Parts` (~20 тис. слів), `XRL.World` (~9.5 тис.),
  `XRL.World.Effects` (~7 тис.) і `XRL.World.Parts.Mutation` (~6.6 тис.: описи мутацій зашиті в
  код, а не в XML).

## Шрифти й символи: де кирилиця працює, а де ні

Гра рендерить текст двома шляхами.

### 1. Сучасний UI (TextMeshPro): кирилиця, **імовірно, працює** (ще не перевірено в грі)

- Текст із розміткою Qud (`&R`, `{{R|…}}`) перетворюється на rich text TMP функцією
  `Sidebar.FormatToRTF` (`XRL.UI/Sidebar.cs`). Вона перекладає коди 0–255 у Unicode за таблицею
  `Codepage437Mapping`, а решту символів лишає як є.
- Шрифти TMP: `SourceCodePro-*` (є **динамічний** `SourceCodePro-Regular SDF Dynamic`),
  `LiberationSans SDF` (fallback), `SourceHanMono SDF` (CJK). У вбудованих даних шрифтів
  Source Code Pro (`sharedassets0.assets`) знайдено гліфи `uni0404/0454` (Є є), `uni0406/0456`
  (І і), `uni0407/0457` (Ї ї), `uni0490/0491` (Ґ ґ), `uni02BC` (ʼ), `uni2116` (№).
- Глобальний список запасних шрифтів — `TMP_Settings.fallbackFontAssets`, гра сама його змінює
  (`ControlManager.cs`). Якщо якогось гліфа бракуватиме, мод може додати туди свій шрифт.
- **Пастка:** символи з кодами 128–255 гра вважає CP437. Якщо вставити в рядок з C#-коду `«`
  (U+00AB = 171), на екрані з'явиться `½`, бо код 171 у CP437 означає ½. У XML цієї проблеми
  немає: там спрацьовує `ToCP437`. Тож рядки, які ми підставляємо з C#, треба або проганяти
  через `Sidebar.ToCP437`, або уникати в них U+0080–U+00FF.

### 2. Консольний шар (карта, класичний UI, частина оверлеїв): кирилиця **невидима**

- Рендер консолі в `GameManager.cs` робить так:
  `if (c < '\0' || c > 'ÿ') c = ' '; exTextureInfo t = CharInfos[(uint)c];`. Тобто **будь-який
  символ із кодом понад 255 малюється як пробіл**. `CharInfos` — це масив рівно на 256 спрайтів
  `assets_content_textures_text_N.bmp`, по одному на гліф CP437.
- Як це виправити (ідея, **не перевірена**):
  - Мод може додати PNG-спрайти в теку `Textures/`. Їх реєструє `Kobold/SpriteManager.cs`, ключ
    дорівнює шляху після `textures/` **[перевірено]**.
  - Файли `Textures/Text/1072.png` (для «а», U+0430) і далі, плюс Harmony-транспайлер, що знімає
    обмеження `> 'ÿ'` і розширює `CharInfos`, мають дати кирилицю в консолі **[припущення]**.
  - Чи збігається ключ спрайта з ключем, який шукає `CharInfos`, ще треба звірити з `GetKey` і
    `KeyPrefix`.
  - Гліфи потрібно намалювати в стилі шрифту гри.
- Шрифт консолі — CP437 (256 гліфів), видно в `StreamingAssets/Base/terminal2.bmp`.

## Процедурна генерація: найважча частина

- `HistorySpice.json` — це «граматика» з підстановками `<spice.….!random>`, `.article`,
  `<entity.subjectPronoun>`. Англійські шаблони на кшталт `<^.adjectives.!random> eyes`
  українською потребують узгодження прикметника з іменником за родом, числом і відмінком.
  Тут доведеться міняти структуру даних (форми слів), а не просто перекладати рядки.
- `LibraryCorpus.json` — корпус марковського генератора текстів книг (`MarkovCorpusGenerator`,
  `GameText.GenerateMarkovMessageParagraph`). Варіанти: лишити англійським, або скласти
  український корпус із суспільного надбання (тоді генеровані книги будуть українською).
- Назви квестів одночасно слугують **ідентифікаторами**:
  `IfHaveActiveQuest="What's Eating the Watervine?"` у діалогах. Перекладати їх треба там, де
  вони показуються, а не в самому ID.
- `TextFilters` (мова птахів, риб, жаб, «Weird», leet, криптична мова машин) і
  `Grammar.Stutterize`/`Weirdify`/`Obfuscate` працюють на англійських словниках і правилах.

## Як повторити вимірювання

Шлях до гри береться зі змінної середовища `QUD_GAME_DIR`. Якщо її немає, використовується
`D:\Steam\steamapps\common\Caves of Qud`.

```bash
py tools/analysis/xmlscan.py            # слова по файлах
py tools/analysis/keyscan.py 40         # які (елемент, атрибут) несуть текст
py tools/analysis/varscan.py            # змінні =...= у текстових полях
dotnet run tools/analysis/asmscan.cs -- ldstr               # рядкові літерали в коді за типами
dotnet run tools/analysis/asmscan.cs -- types "Grammar"     # пошук типів за regex
ilspycmd -p -o work/decompiled/Assembly-CSharp -r "<Managed>" "<Managed>/Assembly-CSharp.dll"
```
