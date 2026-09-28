# Права / Rights

## Українською

- **Caves of Qud** і весь оригінальний вміст гри — текст, код, графіка, звук — належать
  **Freehold Games**. Цей проєкт неофіційний, некомерційний і з Freehold Games не пов'язаний.
- **Код** репозиторію (`tools/`, скрипти, майбутній C#-код моду) поширюється за ліцензією MIT
  (`LICENSE`).
- **Текст перекладу** (`translations/`) — похідна робота від тексту гри, і MIT на нього **не**
  поширюється:
  - права на оригінал лишаються за Freehold Games;
  - переклад призначений лише для некомерційного використання разом із грою.
- **Чого в репозиторії немає:** файлів гри, декомпільованого коду й англійського тексту гри.
  - У `translations/` лежить лише наш український текст, а одиниці перекладу позначені хешами,
    без англійського оригіналу.
  - Англійський текст потрібен лише локально: інструменти беруть його з копії гри, яка є в
    кожного, хто працює з перекладом.
  - Невеликі цитати в документації й тестах ілюструють технічні питання.
  - Глосарій (`glossary/terms.tsv`) — список окремих назв і термінів гри з українськими
    відповідниками, а не текст гри.
- Готові файли моду (`mod/Language/*.uk.xml`) генеруються й поширюються лише як сам мод. Формат
  локалізації Freehold вимагає, щоб у них були англійські ідентифікатори рядків (для таблиць
  рядків ідентифікатор — це англійський текст). Англійською лишаються й неперекладені частини
  записів, які гра замінює цілком.
- Якщо Freehold Games попросять щось прибрати або змінити, ми зробимо це одразу.

## In English

- **Caves of Qud** and all of its original content (text, code, art, audio) belong to
  **Freehold Games**. This is an unofficial, non-commercial fan project, not affiliated with
  Freehold Games.
- The **code** in this repository (`tools/`, scripts, the mod's future C# code) is MIT-licensed
  (`LICENSE`).
- The **translation text** (`translations/`) is a derivative of the game's text and is **not**
  covered by the MIT license:
  - all rights in the original remain with Freehold Games;
  - the translation is meant for non-commercial use with the game only.
- **What the repository does not contain:** game files, decompiled code, or the game's English
  text.
  - `translations/` holds only our Ukrainian text, with units identified by hashes rather than
    by the English source.
  - The English text is only needed locally; the tools read it from each contributor's own copy
    of the game.
  - Short quotations in the documentation and tests illustrate technical points.
  - The glossary (`glossary/terms.tsv`) lists individual names and terms from the game with their
    Ukrainian equivalents, not the game's text.
- The built mod files (`mod/Language/*.uk.xml`) are generated and distributed only as the mod
  itself. Freehold's localization format requires them to contain English string IDs (for string
  tables the ID is the English text). Untranslated parts of entries that the game replaces as a
  whole also stay in English there.
- If Freehold Games ask us to remove or change anything, we will do so promptly.
