# CLAUDE.md — Caves of Qud українською

Інструкції для сесій Claude в цьому репозиторії. Мова спілкування з Mike — українська.
Ідентифікатори й коментарі в коді — англійською.

## Що це за проєкт

Український переклад Caves of Qud як мод для офіційного фреймворку локалізації (гілка Steam
`lang-experimental`, збірки 2.0.212+). Рішення й причини — `docs/decisions.md`, план і питання —
`docs/plan.md`, стиль — `docs/style-guide.md`. Перш ніж щось робити, прочитай `docs/plan.md` і
потрібні файли з `docs/research/`. Головний технічний документ — `docs/research/framework-212.md`.

## Робоча дисципліна

- **Вимірюй, а не припускай.** Твердження про поведінку гри перевіряй у декомпільованому коді
  або в самій грі. У документах позначай, що перевірено, а що ні (**[перевірено]**,
  **[за звітом]**, **[припущення]**).
- **Не довіряй запобіжнику, поки не побачив, як він спрацьовує.** Валідатор чи перевірку спершу
  зламай навмисно й переконайся, що вона ловить поломку.
- Етап плану закінчується розділом «Підсумок» у `docs/plan.md`: що зроблено, що виміряно, що
  лишилося неперевіреним.

## Авторське право (рішення D7) — обов'язково

- У git іде **лише наш текст**: `translations/uk/*.jsonl` (український переклад, одиниці
  позначені хешами), код (MIT), документація.
- **Ніколи не комітити:**
  - англійський текст гри, зокрема PO-файли: у них `msgid` — оригінал;
  - код і дані гри, `work/`;
  - згенеровані `mod/Language/*.uk.xml`: вони містять англійські ID і йдуть лише в релізи.
- Запобіжники вже стоять:
  - `.gitignore` для `work/`, `mod/Language/*.uk.xml`, `translations/**/*.po`;
  - тест `NoEnglishInTheStore`.
  Не обходь їх. Перед комітом перевір `git diff --cached --stat`.
- Короткі цитати гри в документації й тестах — лише для пояснення технічних питань.

## Git

- У **цьому** репозиторії Claude може комітити й пушити (рішення D2). Коміти — завершені логічні
  кроки з ясними повідомленнями. Remote: `https://github.com/mikeKuharuk/Caves-of-Qud-UA`
  (публічний).
- Інші публічні дії (Workshop, пости, повідомлення Freehold) — лише після згоди Mike.

## Шляхи

| Що | Де |
|---|---|
| Гра | `D:\Steam\steamapps\common\Caves of Qud` (або `$env:QUD_GAME_DIR`) |
| Англійські таблиці рядків | `CoQ_Data\StreamingAssets\Base\ExampleLanguage\` |
| Код гри | `CoQ_Data\Managed\Assembly-CSharp.dll` |
| Моди, логи, опції | `%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\` (`Mods\`, `Player.log`, `build_log.txt`, `Local\PlayerOptions.json`) |
| Переклад у git | `translations/uk/*.jsonl` |
| Робочі PO (з англійським) | `work/po/uk/*.po` (локально) |
| Декомпільований код | `work/decompiled/<версія>/Assembly-CSharp/` (є `2.0.211.56` і `2.0.212.31`) |
| Таблиці рядків по збірках | `work/example-language/` (git-дзеркало gnarf, теги `212.x`) |
| Збережені логи гри | `work/logs/` |

Декомпіляція (ilspycmd встановлено глобально):
`ilspycmd -p -o work/decompiled/<версія>/Assembly-CSharp -r "<Managed>" "<Managed>\Assembly-CSharp.dll"`

## Робочий цикл перекладу

```bash
py tools/qud.py sync        # англійське з гри + translations/ → work/po/uk/*.po (і назад у translations/)
py tools/qud.py save        # після редагування PO: work/po/uk/*.po → translations/uk/*.jsonl
py tools/qud.py validate    # 0 помилок перед кожним комітом
py tools/qud.py build       # → mod/Language/*.uk.xml (генеровані, руками не редагувати)
py tools/qud.py stats       # прогрес
py tools/qud.py worksheet Skills.po --out work/batch/Skills.jsonl   # неперекладене → пакет JSONL
py tools/qud.py check-worksheet work/batch/Skills.uk.jsonl          # перевірити пакет, не чіпаючи PO
py tools/qud.py apply work/batch/Skills.uk.jsonl                    # заповнений пакет → PO
py -m unittest discover -s tools/tests   # 72 тести, зокрема на реальних даних гри
```

- Пакети (`work/batch/`, не в git) — зручний спосіб перекладати великими порціями:
  - `apply` відмовляє на помилках розмітки й на одиницях, яких уже немає в PO;
  - рядок пакета може мати `"comment"` (коментар перекладача; кілька — через `\n`) і
    `"fuzzy": true`.
- Великі обсяги перекладають паралельні субагенти за брифом `docs/translator-brief.md`:
  - кожен пише лише свої `work/batch/<пакет>_uk*.py` і перевіряє їх
    `work/batch/merge_uk.py <пакет>`;
  - координатор застосовує пакети, робить вибіркову вичитку, `validate` і коміт;
  - локальні скрипти: `make_chunks.py` (порції з підказкою `name_uk`), `make_names.py` (унікальні
    назви й розкладання їх назад по файлах).
- Свідоме відхилення, яке `validate` показує як попередження (наприклад, прибрана англійська
  `|pluralize`), позначай коментарем перекладача `qud-ok: <код> — причина`. Помилки так не
  приймаються.
- Після оновлення гри: декомпілювати нову збірку й перегенерувати список ключів змінних для
  `validate`: `py tools/analysis/replacers.py work/decompiled/<версія>/Assembly-CSharp`.
- Перекладаєш у `work/po/uk/*.po`: заповнюєш `msgstr`. Потім `save` і коміт `translations/`.
- Переклади Claude йдуть одразу в збірку, без `fuzzy` (D8). Mike вичитує в грі й у PO.
- Після `git pull` чужих змін: `sync --from-store`.
- `mod/Language/Languages.xml` — єдиний рукописний файл у `mod/Language/`.

## Тестування в грі

- **Гру запускати й керувати комп'ютером (computer-use) — лише коли Mike прямо дозволив у цій
  розмові** (з 2026-09-28 він працює за комп'ютером паралельно). Без дозволу — лише файли, скрипти,
  збірка. Неперевірене в грі так і позначати, перевірку пропонувати, коли Mike скаже.
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

## Правила перекладу (коротко; повністю — `docs/style-guide.md`)

- До гравця звертаємося на «ви», з малої літери (D3). Власні назви — за D4. Апостроф — `’`.
- Не перекладати й не змінювати:
  - `=змінні=`: їх можна переставляти в реченні;
  - ідентифікатори шейдерів `{{id|…}}`: перекладається лише текст праворуч від `|`;
  - коди кольорів `&X` і `^X`;
  - клавіші `~CmdX`;
  - ключі в складених значеннях `▶` (прапорець `qud-compound`).
- Жорсткі переноси рядків з англійського оригіналу не копіювати.
- Нічого не вигадувати про гру: незрозумілий термін чи контекст шукати в
  `work/example-language`, декомпільованому коді або вікі, а не вгадувати.
