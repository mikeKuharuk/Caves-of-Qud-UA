# Реліз у Steam Workshop

Мод завантажує в Workshop сама гра: «Mods» → мод «Українська мова (Ukrainian)» → завантажувач Workshop
(`SteamWorkshopUploaderView`). Він бере теку мода як є, без прихованих файлів і посилань, і читає з
`mod/workshop.json` назву, опис (BBCode), теги, видимість і прев’ю (`mod/preview.png`, 512×512, малює
`tools/preview.ps1`). Після першого завантаження гра записує в `workshop.json` номер предмета (`WorkshopId`). Цей
файл треба закомітити: наступні завантаження оновлюють той самий предмет.

## Рішення: публікувати, як інші, з приміткою про права (Mike, 2026-10-06)

Зібраний мод містить англійський текст гри: таблиці рядків фреймворку мають англійський оригінал як ідентифікатор
(`ID="…"` у `mod/Language/*.uk.xml`; так влаштований сам фреймворк — `StringsLoader` шукає переклад за `Context` і
`ID`), а кодові таблиці (`mod/Grammar/CodeTables.g.cs`) мають ключами англійський текст із коду гри. У git їх немає:
вони лише в зібраному моді, який іде в Workshop. Так само роблять інші переклади: традиційний китайський (Aosaki
Reiya, той самий фреймворк, файли з англійськими `ID` і в Workshop, і на GitHub) і японський «QudJP» (ToaruPen,
стабільна гілка, Harmony і копії XML гри). Явного дозволу Freehold ні в кого не згадано.

Тому опис у `workshop.json` має розділ «Права» українською й англійською: гра і її текст належать Freehold Games,
переклад неофіційний і некомерційний, англійський текст — лише ідентифікатори, яких вимагає фреймворк; на прохання
Freehold мод приберемо. Лист Freehold (**Q4**, [`docs/freehold-report.md`](freehold-report.md)) реліз не блокує,
але його варто надіслати.

## Порядок релізу

1. Гра на `lang-experimental`, та сама збірка, з якої зроблено переклад (зараз 2.0.212.31).
2. Зібрати й перевірити:
   - `py tools/qud.py build`;
   - `py tools/qud.py validate` — 0 помилок;
   - `py -m unittest discover -s tools/tests`;
   - `dotnet build tools/grammar-build` і `dotnet run --project tools/patch-tests`;
   - запустити гру, у `build_log.txt` — «Compiling … Success» і «Applying Harmony patches… Success»;
   - у грі wish (Ctrl+W) `testlangreplacers`: вікно з переліком змінних відкривається, а в
     `Local/VariableReplacers.txt` (поруч із `Player.log`) немає жодного «!=» — приклади замінників мода збіглися.
3. Номер версії — `Version` у `mod/manifest.json` (гра пише його в тег предмета `manifest_version`).
4. Завантажити з гри (Mike): «Mods» → мод → кнопка Workshop. Перше завантаження просить прийняти угоду Steam
   Workshop — це робить Mike, на сторінці Steam. Видимість у `workshop.json` — `Private`: перевірити сторінку
   предмета, тоді перемкнути на `Public`.
5. Закомітити `mod/workshop.json` з номером предмета.

## Оновлення

Зібрати й перевірити (крок 2), підняти `Version`, завантажити з того самого мода з нотатками змін.
