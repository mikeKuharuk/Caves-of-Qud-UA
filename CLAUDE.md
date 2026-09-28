# CLAUDE.md — Caves of Qud українською

Інструкції для сесій Claude в цьому репозиторії. Мова спілкування з Mike — українська.
Ідентифікатори й коментарі в коді — англійською.

## Що це за проєкт

Український переклад Caves of Qud як мод для офіційного фреймворку локалізації (гілка Steam
`lang-experimental`, збірки 2.0.212+). Рішення й причини — `docs/decisions.md`, план і питання —
`docs/plan.md`. Перш ніж щось робити, прочитай `docs/plan.md` і потрібні файли з
`docs/research/`. Головний технічний документ — `docs/research/framework-212.md`.

## Робоча дисципліна

- **Вимірюй, а не припускай.** Твердження про поведінку гри перевіряй у декомпільованому коді
  або в самій грі. У документах позначай, що перевірено, а що ні (**[перевірено]**,
  **[за звітом]**, **[припущення]**).
- **Не довіряй запобіжнику, поки не побачив, як він спрацьовує.** Валідатор чи перевірку спершу
  зламай навмисно й переконайся, що вона ловить поломку.
- Етап плану закінчується розділом «Підсумок» у `docs/plan.md`: що зроблено, що виміряно, що
  лишилося неперевіреним.

## Git

- У **цьому** репозиторії Claude може комітити й пушити (рішення D2). Коміти — завершені логічні
  кроки з ясними повідомленнями. Remote: `https://github.com/mikeKuharuk/Caves-of-Qud-UA`.
- Інші публічні дії (Workshop, пости, листи Freehold) — лише після згоди Mike.
- **Ніколи не комітити** код гри, її дані чи їхні великі фрагменти: `work/decompiled/`,
  `work/example-language/`, `work/logs/`, копії `StreamingAssets`. Це авторське право Freehold.
  Переклад — наш текст, його комітимо.
- `translations/uk/*.po` містять як `msgid` **весь англійський текст** таблиць рядків (той самий,
  що Freehold публікують для перекладачів у gnarf/caves-of-qud-example-language), а репозиторій
  публічний. Поки Mike не вирішить питання Q4 (ліцензія / лист Freehold), PO **не комітити й
  не пушити**: вони лежать лише локально.

## Шляхи

| Що | Де |
|---|---|
| Гра | `D:\Steam\steamapps\common\Caves of Qud` (або `$env:QUD_GAME_DIR`) |
| Дані гри | `CoQ_Data\StreamingAssets\Base\` (таблиці рядків — `ExampleLanguage\`) |
| Код гри | `CoQ_Data\Managed\Assembly-CSharp.dll` |
| Моди, логи, опції | `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\` (`Mods\`, `Player.log`, `build_log.txt`, `Local\PlayerOptions.json`) |
| Декомпільований код | `work/decompiled/<версія>/Assembly-CSharp/` (є `2.0.211.56` і `2.0.212.31`) |
| Таблиці рядків по збірках | `work/example-language/` (git-дзеркало gnarf, теги `212.x`) |
| Збережені логи гри | `work/logs/` |

Декомпіляція (ilspycmd встановлено глобально):
`ilspycmd -p -o work/decompiled/<версія>/Assembly-CSharp -r "<Managed>" "<Managed>\Assembly-CSharp.dll"`

## Робочий цикл перекладу

```bash
py tools/qud.py sync        # англійські таблиці рядків (з гри) → translations/uk/*.po
py tools/qud.py validate    # 0 помилок перед кожним комітом
py tools/qud.py build       # PO → mod/Language/*.uk.xml (генеровані, руками не редагувати)
py tools/qud.py stats       # прогрес
py -m unittest discover -s tools/tests   # 44 тести, зокрема на реальних даних гри
```

- Перекладаєш у `translations/uk/*.po`: заповнюєш `msgstr`.
- Пропозиція, яку Mike ще не підтвердив: чернетки Claude позначати `fuzzy`, доки Mike їх не
  вичитає. Fuzzy не потрапляє в збірку, а для тесту в грі є `build --include-fuzzy`.
- `mod/Language/Languages.xml` — єдиний рукописний файл у `mod/Language/`.
- Стиль — `docs/style-guide.md`.

## Тестування в грі

- `powershell -File tools/deploy.ps1` підключає `mod/` до гри через junction (`-Remove` прибирає).
- Запускати **лише через Steam**: `Start-Process steam://rungameid/333640`. Computer-use
  `open_application` запускає **другу** копію гри напряму — так не робити. Вікно гри
  розгортає `SetForegroundWindow`. У request_access застосунок називається `CoQ.exe`.
- Через computer-use гра не отримує клавішу Escape. Виходити назад кнопкою «[Esc] Back» або
  правою кнопкою миші. Закривати гру — `CloseMainWindow()`: вона виходить одразу, без
  підтвердження.
- Корисні опції (Debug → «Show Debug (Translation) options», потрібні «Show advanced options»):
  «Log string table lookup misses…» (промахи → `Player.log` → `py tools/misses.py`) і «Enable
  extra strings xml loading checks». Для швидкої нової гри є «Show quickstart option during
  character creation».
- Зміна мови й зміна файлів перекладу вимагають перезапуску гри.

## Правила перекладу (попередні, до появи `docs/style-guide.md`)

- До гравця звертаємося на «ви», з малої літери (D3). Власні назви — за D4.
- Кожен файл перекладу має корінь з `Lang="uk" Encoding="utf-8"`, називається `*.uk.xml` і
  лежить у `mod/Language/`. Джерело правди — PO (D5), XML генерується.
- Не перекладати й не змінювати:
  - `=змінні=`: їх можна переставляти в реченні;
  - ідентифікатори шейдерів `{{id|…}}`: перекладається лише текст праворуч від `|`;
  - коди кольорів `&X` і `^X`;
  - клавіші `~CmdX`;
  - розділювачі альтернатив `~`;
  - ключові поля, які хибно позначені `▶`: `xtagGrammar` (`massNoun`, `Proper`),
    `ArmsOnEquip`, `Category`, назви слотів тіла й кольорів.
- У таблицях рядків `ID` — англійський оригінал. Його не змінювати: перекладається лише вміст
  елемента або `Value`.
- Жорсткі переноси рядків з англійського оригіналу не копіювати. Абзаци переносить UI; наші
  рядки іншої довжини, і ламані переноси виглядають погано (перевірено в довідці).
- Нічого не вигадувати про гру: незрозумілий термін чи контекст шукати в
  `work/example-language`, декомпільованому коді або вікі, а не вгадувати.
