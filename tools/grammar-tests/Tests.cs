using System;
using System.Collections.Generic;
using CavesOfQudUA.Grammar;

static class Tests
{
    static int failures;

    static void Eq(string expected, string actual, string what)
    {
        if (expected == actual) return;
        failures++;
        Console.WriteLine($"FAIL {what}: expected «{expected}», got «{actual}»");
    }

    static int Main()
    {
        string[] turns = { "хід", "ходи", "ходів" };
        var numbers = new Dictionary<long, string>
        {
            [0] = "ходів", [1] = "хід", [2] = "ходи", [4] = "ходи", [5] = "ходів", [11] = "ходів", [12] = "ходів",
            [14] = "ходів", [21] = "хід", [22] = "ходи", [25] = "ходів", [101] = "хід", [111] = "ходів", [-3] = "ходи",
        };
        foreach (var pair in numbers)
            Eq(pair.Value, UkrainianForms.ByNumber(pair.Key, turns), $"plural of {pair.Key}");
        Eq("драм", UkrainianForms.ByNumber(5, new[] { "драм" }), "a single form stands in for all");

        // the counts the code writes with Extensions.Things
        Eq("1 хід", UkrainianThings.Count(1, "1", "turn"), "1 turn");
        Eq("5 ходів", UkrainianThings.Count(5, "5", "round"), "5 rounds");
        Eq("ще 3 ходи", UkrainianThings.Count(3, "3", "more turn"), "3 more turns");
        Eq("21 клітинка", UkrainianThings.Count(21, "21", "square"), "21 squares");
        Eq("12 драмів", UkrainianThings.Count(12, "12", "dram"), "12 drams");
        Eq("2 очки мутацій", UkrainianThings.Count(2, "2", "mutation point"), "2 mutation points");
        Eq("2,5 клітинки", UkrainianThings.Count(2.5, "2,5", "square"), "a number that is not whole");
        Eq("стріла ×3", UkrainianThings.Count(3, "3", "стріла"), "a Ukrainian name has no plural to give");
        Eq(null, UkrainianThings.Count(3, "3", "widget"), "an English word we do not know stays with the game");

        // body parts' sides and ordinals (the game's bits: left 1, right 2, upper 4, lower 8, fore 16, mid 32, hind 64)
        Eq("ліва рука", UkrainianLaterality.With("рука", 1, UkGender.Feminine, false), "left arm");
        Eq("Ліва рука", UkrainianLaterality.With("Рука", 1, UkGender.Feminine, true), "Left Arm, capitalized");
        Eq("верхній правий ріг", UkrainianLaterality.With("ріг", 4 | 2, UkGender.Masculine, false), "upper right horn");
        Eq("праве заднє крило", UkrainianLaterality.With("крило", 2 | 64, UkGender.Neuter, false), "right hind wing");
        Eq("ліві середньо-передні ноги", UkrainianLaterality.With("ноги", 1 | 32 | 16, UkGender.Plural, false), "left mid-fore");
        Eq("голова", UkrainianLaterality.With("голова", 0, UkGender.Feminine, false), "no laterality");
        Eq("рука", UkrainianLaterality.Strip("ліва рука", 1, false), "strip");
        Eq("Ріг", UkrainianLaterality.Strip("Верхній правий ріг", 4 | 2, true), "strip, capitalized");
        Eq("права рука", UkrainianLaterality.Strip("права рука", 1, false), "strip only the laterality's own words");
        Eq("друга голова", UkrainianLaterality.WithOrdinal(2, "голова", UkGender.Feminine, false), "second head");
        Eq("Третя ліва рука", UkrainianLaterality.WithOrdinal(3, "Ліва рука", UkGender.Feminine, true), "Third Left Arm");
        Eq("другий ріг", UkrainianLaterality.WithOrdinal(2, "ріг", UkGender.Masculine, false), "second horn");

        string[] fell = { "упав", "упала", "упало", "упали" };
        Eq("упав", UkrainianForms.ByGender(UkGender.Masculine, fell), "masculine");
        Eq("упала", UkrainianForms.ByGender(UkGender.Feminine, fell), "feminine");
        Eq("упало", UkrainianForms.ByGender(UkGender.Neuter, fell), "neuter");
        Eq("упали", UkrainianForms.ByGender(UkGender.Plural, fell), "plural");
        Eq("готовий", UkrainianForms.ByGender(UkGender.Neuter, new[] { "готовий", "готова" }), "a missing neuter takes the masculine");
        Eq("готова", UkrainianForms.ByGender(UkGender.Plural, new[] { "готовий", "готова" }), "a missing plural takes the last form");

        string[] him = { "його", "її", "його", "їх", "вас" };
        Eq("вас", UkrainianForms.ByGenderOrPlayer(true, UkGender.Masculine, him), "the player's own fifth form");
        Eq("їх", UkrainianForms.ByGenderOrPlayer(false, UkGender.Plural, him), "a plural object is not the player");
        Eq("її", UkrainianForms.ByGenderOrPlayer(false, UkGender.Feminine, him), "feminine");
        Eq("упали", UkrainianForms.ByGenderOrPlayer(true, UkGender.Masculine, fell), "no fifth form: the player takes the plural");

        string[] hits = { "б’є", "б’єте", "б’ють" };
        Eq("б’єте", UkrainianForms.ByPerson(true, false, hits), "the player is «ви»");
        Eq("б’є", UkrainianForms.ByPerson(false, false, hits), "3rd person singular");
        Eq("б’ють", UkrainianForms.ByPerson(false, true, hits), "3rd person plural");
        Eq("б’є", UkrainianForms.ByPerson(false, true, new[] { "б’є", "б’єте" }), "no plural form given");

        Eq("Masculine", UkrainianForms.FromGameGender("male", false, false).ToString(), "male");
        Eq("Feminine", UkrainianForms.FromGameGender("female", false, false).ToString(), "female");
        Eq("Neuter", UkrainianForms.FromGameGender("elverson", false, false).ToString(), "ey/em is neuter (D11)");
        Eq("Plural", UkrainianForms.FromGameGender("plural", true, false).ToString(), "plural");
        Eq("", UkrainianForms.FromGameGender("neuter", false, false).ToString(), "things follow their noun");
        Eq("Plural", UkrainianForms.FromGameGender("some generated", false, true).ToString(), "a pseudo-plural gender");
        Eq("Feminine", UkrainianForms.FromLetter("f").ToString(), "qud-gender letter");

        var table = new Dictionary<string, string[]> { ["іржавий"] = new[] { "іржава", "іржаве", "іржаві" },
                                                       ["вкритий рідиною"] = new[] { "вкрита рідиною", "вкрите рідиною", "вкриті рідиною" } };
        Func<string, string[]> lookup = w => table.TryGetValue(w, out var f) ? f : null;
        Eq("іржава", UkrainianForms.AgreeAdjective("іржавий", UkGender.Feminine, lookup), "feminine adjective");
        Eq("{{K|іржаве}}", UkrainianForms.AgreeAdjective("{{K|іржавий}}", UkGender.Neuter, lookup), "inside markup");
        Eq("&rіржаві", UkrainianForms.AgreeAdjective("&rіржавий", UkGender.Plural, lookup), "after a colour code");
        Eq("іржавий", UkrainianForms.AgreeAdjective("іржавий", UkGender.Masculine, lookup), "masculine stays");
        Eq("вкрита рідиною", UkrainianForms.AgreeAdjective("вкритий рідиною", UkGender.Feminine, lookup), "a phrase");
        Eq("{{c|фазоспряжений}}", UkrainianForms.AgreeAdjective("{{c|фазоспряжений}}", UkGender.Feminine, lookup), "not in the table");
        Eq("іржавий", UkrainianForms.StripMarkup("{{K|іржавий}}"), "strip markup");
        Eq("{{c|фазоспряжена}}", UkrainianForms.AgreeAdjective("{{c|фазоспряжений}}", UkGender.Feminine, lookup, regular: true),
           "not in the table, regular endings");
        Eq("{{r|іржаві}} і {{m|вкриті рідиною}}",
           UkrainianForms.AgreeAdjective("{{r|іржавий}} і {{m|вкритий рідиною}}", UkGender.Plural, lookup), "two joined adjectives");
        Eq("іржава, синя", UkrainianForms.AgreeAdjective("іржавий, синій", UkGender.Feminine, lookup, regular: true),
           "a joined adjective not in the table");

        Eq("сіра", UkrainianForms.InflectRegular("сірий", UkGender.Feminine), "hard -ий");
        Eq("синє", UkrainianForms.InflectRegular("синій", UkGender.Neuter), "soft -ій");
        Eq("безкраї", UkrainianForms.InflectRegular("безкраїй", UkGender.Plural), "-їй");
        Eq("чорно-біла", UkrainianForms.InflectRegular("чорно-білий", UkGender.Feminine), "a hyphenated compound");
        Eq("заплямована кров’ю", UkrainianForms.InflectRegular("заплямований кров’ю", UkGender.Feminine), "a participle phrase");
        Eq("Зла", UkrainianForms.InflectRegular("Злий", UkGender.Feminine), "capital letter");
        Eq("Рух", UkrainianForms.InflectRegular("Рух", UkGender.Feminine), "a noun stays");
        Eq("сірий", UkrainianForms.InflectRegular("сірий", UkGender.Masculine), "masculine stays");
        var ordinals = new Dictionary<string, string>
        {
            ["1-й"] = "1-ша", ["2-й"] = "2-га", ["3-й"] = "3-тя", ["4-й"] = "4-та", ["7-й"] = "7-ма", ["8-й"] = "8-ма",
            ["9-й"] = "9-та", ["10-й"] = "10-та", ["11-й"] = "11-та", ["13-й"] = "13-та", ["21-й"] = "21-ша",
            ["23-й"] = "23-тя", ["30-й"] = "30-та", ["0-й"] = "0-ва", ["-1-й"] = "-1-ша", ["40-й"] = "40-ва",
        };
        foreach (var pair in ordinals)
            Eq(pair.Value, UkrainianForms.InflectRegular(pair.Key, UkGender.Feminine), $"ordinal {pair.Key}");
        Eq("3-тє", UkrainianForms.InflectRegular("3-й", UkGender.Neuter), "neuter ordinal");
        Eq("2-гі", UkrainianForms.InflectRegular("2-й", UkGender.Plural), "plural ordinal");

        Eq("Скопа", CodeWords.Translate("Osprey"), "a word from the code");
        Eq("Unknown", CodeWords.Translate("Unknown"), "an unknown word stays");
        CodeTables.Add("Words", "Wander", "мандрівний режим");
        Eq("мандрівний режим", CodeWords.Translate("Wander"), "a word the Words code table has");
        Eq("Feminine", CodeWords.GenderOf("Owl").ToString(), "gender by the English word");
        Eq("Masculine", CodeWords.GenderOf("Орел").ToString(), "gender by the Ukrainian word");

        // names in a case (UkrainianCases), as the game's names stand in the translation
        foreach (string adjective in new[] { "шкіряний", "фугасний", "велетенський", "поїдений", "молодий", "слоновий",
                                             "базовий", "механічний", "жовтушний", "сирий", "вигнутий", "великий",
                                             "херувимський", "задушливий", "ходячий", "вогняний", "печерний",
                                             "гравірований", "мармуровий", "письмовий", "обліплений" })
            AdjectiveLexicon.Add(adjective);
        AdjectiveLexicon.AddNoun("дочка");   // the build learns it from «apple farmer's daughter»
        AdjectiveLexicon.AddFeminineStem("труб");               // «трубою»
        AdjectiveLexicon.AddFeminineStem("пісн", soft: true);    // «піснею»
        AdjectiveLexicon.AddFeminineStem("тін", third: true);    // «тінню»
        string In(string name, UkGender gender, bool animate, UkCase c) => UkrainianCases.Inflect(name, gender, animate, c);
        var M = UkGender.Masculine; var F = UkGender.Feminine; var N = UkGender.Neuter; var P = UkGender.Plural;
        var gen = UkCase.Genitive; var dat = UkCase.Dative; var acc = UkCase.Accusative; var ins = UkCase.Instrumental;
        var loc = UkCase.Locative;
        // masculine: an animate accusative is the genitive, an inanimate one the nominative
        Eq("пащеклаца", In("пащеклац", M, true, acc), "an animate masculine accusative");
        Eq("пащеклацові", In("пащеклац", M, true, dat), "an animate masculine dative");
        Eq("пащеклацом", In("пащеклац", M, true, ins), "a masculine instrumental");
        Eq("меч", In("меч", M, false, acc), "an inanimate masculine accusative");
        Eq("меча", In("меч", M, false, gen), "a masculine genitive");
        Eq("мечем", In("меч", M, false, ins), "a sibilant's instrumental");
        Eq("базового ведмедя", In("базовий ведмідь", M, true, acc), "an adjective and an irregular noun");
        Eq("механічного херувима-павіана", In("механічний херувим-павіан", M, true, gen), "a hyphenated noun, both parts");
        Eq("іссахарі-рейдера", In("іссахарі-рейдер", M, true, acc), "an indeclinable part stays");
        Eq("майстра турелей", In("майстер турелей", M, true, acc), "the genitive after the head stays");
        Eq("трупом печерного павука", In("труп печерного павука", M, false, ins), "an inanimate head before a genitive");
        Eq("мішка", In("мішок", M, false, gen), "a vowel that drops");
        Eq("мішку", In("мішок", M, false, loc), "a locative after к");
        Eq("гаманцем", In("гаманець", M, false, ins), "-ець");
        Eq("ліхтаря", In("ліхтар", M, false, gen), "a soft -ар");
        Eq("Мехрока", In("Мехрок", M, true, acc), "a proper name keeps its vowel");
        Eq("Андрієм", In("Андрій", M, true, ins), "a name on -ій is a noun");
        // feminine
        Eq("шкіряну броню", In("шкіряна броня", F, false, acc), "a feminine accusative, soft");
        Eq("шкіряною бронею", In("шкіряна броня", F, false, ins), "a feminine instrumental, soft");
        Eq("{{W|фугасну}} гранату Mk I", In("{{W|фугасна}} граната Mk I", F, false, acc), "markup and a mark stay");
        Eq("{{W|фугасній}} гранаті Mk I", In("{{W|фугасна}} граната Mk I", F, false, dat), "a feminine dative");
        Eq("дочці фермера яблук", In("дочка фермера яблук", F, true, dat), "к → ц, the genitives after it stay");
        Eq("поїденою іржею пилкою", In("поїдена іржею пилка", F, false, ins), "an instrumental between adjective and head");
        Eq("молодої слонової кості", In("молода слонова кість", F, false, gen), "a feminine on a consonant");
        Eq("велетенську амебу", In("велетенська амеба", F, true, acc), "a feminine accusative, animate alike");
        Eq("змією", In("змія", F, true, ins), "-ія");
        Eq("сталлю", In("сталь", F, false, ins), "a doubled consonant");
        Eq("кашею", In("каша", F, false, ins), "a sibilant feminine");
        Eq("руці", In("рука", F, false, loc), "к → ц in the locative");
        // neuter
        Eq("жовтушного сяйва", In("жовтушне сяйво", N, false, gen), "a neuter genitive");
        Eq("жовтушному сяйві", In("жовтушне сяйво", N, false, loc), "a neuter locative");
        Eq("сирого м’яса крокодила", In("сире м’ясо крокодила", N, false, gen), "a neuter with an apostrophe");
        Eq("алое порта", In("алое порта", N, false, gen), "a loanword stays");
        Eq("яйцем", In("яйце", N, false, ins), "-е");
        // plural
        Eq("вигнутих рогів", In("вигнуті роги", P, false, gen), "a plural genitive");
        Eq("вигнуті роги", In("вигнуті роги", P, false, acc), "an inanimate plural accusative");
        Eq("великими жвалами", In("великі жвала", P, false, ins), "a neuter plural");
        Eq("ікол", In("ікла", P, false, gen), "a vowel between two consonants");
        Eq("рукавичок", In("рукавички", P, false, gen), "-ки → -ок");
        Eq("кігтями", In("кігті", P, false, ins), "a soft plural");
        Eq("ходячих ібисів", In("ходячі ібиси", P, true, acc), "an animate plural accusative");
        Eq("людей", In("люди", P, true, acc), "an irregular plural");
        Eq("модифікацій", In("модифікації", P, false, gen), "-ії → -ій");
        Eq("зябер", In("зябра", P, false, gen), "е before р");
        Eq("ніші становлення", In("ніша становлення", F, false, gen), "a noun before a verbal noun");
        Eq("гіперпружних сухожиль", In("гіперпружні сухожилля", P, false, gen), "an adjective before a plural on -лля");
        Eq("почуттів", In("почуття", P, false, gen), "-ття → -ттів");
        Eq("сторінки Шредінгера з Літописів", In("сторінка Шредінгера з Літописів", F, false, gen), "a noun before a proper name");
        Eq("{{B|сапфірову}} статуетку", In("{{B|сапфірова}} статуетка", F, false, acc), "an adjective the lexicon lacks");
        // masculine: -у, alternations, soft and hard -ар, the dropping о
        Eq("письмового стола", In("письмовий стіл", M, false, gen), "і → о");
        Eq("мосту на південь", In("міст на південь", M, false, gen), "і → о with -у");
        Eq("газу", In("газ", M, false, gen), "a substance takes -у");
        Eq("клею", In("клей", M, false, gen), "a soft substance takes -ю");
        Eq("сланцю", In("сланець", M, false, gen), "-ець with -ю");
        Eq("самоцвіту", In("самоцвіт", M, false, gen), "a compound of -цвіт");
        Eq("радара", In("радар", M, false, gen), "a thing on -ар is hard");
        Eq("ліхтаря", In("ліхтар", M, false, gen), "but not ліхтар");
        Eq("аптекаря", In("аптекар", M, true, acc), "a person on -ар is soft");
        Eq("панцира", In("панцир", M, false, gen), "-ир is hard");
        Eq("упиря", In("упир", M, true, acc), "but not упир");
        Eq("блока", In("блок", M, false, gen), "no vowel drops from блок");
        Eq("огірка", In("огірок", M, false, gen), "a vowel drops from огірок");
        Eq("пса", In("пес", M, true, acc), "пес → пса");
        Eq("релікварію повернення", In("релікварій повернення", M, false, gen), "-арій is a noun");
        Eq("вартового", In("вартовий", M, true, acc), "an adjective that names a person");
        Eq("голема-мопанго-колісничого", In("голем-мопанго-колісничий", M, true, gen), "the same inside a compound");
        Eq("гамма-метелика", In("гамма-метелик", M, true, acc), "a prefix stays");
        Eq("Фіне", In("Фіне", M, true, gen), "a masculine on -е is foreign");
        Eq("моа", In("моа", F, true, gen), "a vowel before -а: a loanword");
        Eq("{{m|тако супрема}}", In("{{m|тако супрема}}", N, false, gen), "тако never changes");
        Eq("Ґям’йо", In("Ґям’йо", N, true, gen), "nor a name on -йо");
        // other genders
        Eq("{{K|обліплених дьогтем кісток}}", In("{{K|обліплені дьогтем кістки}}", P, false, gen), "a masculine instrumental between");
        Eq("пишно гравірованих мармурових дверей", In("пишно гравіровані мармурові двері", P, false, gen), "an adverb before");
        Eq("екуемекійської зелені", In("екуемекійська зелень", F, false, gen), "-ська before a noun on -ь");
        Eq("гвинтівкової турелі", In("гвинтівкова турель", F, false, gen), "an unknown adjective before -ь");
        Eq("зупинки самохода", In("зупинка самохода", F, false, gen), "-ка is a noun");
        Eq("Про мімікрію", In("Про мімікрію", F, false, gen), "a title on a preposition stays");
        Eq("троленяти", In("троленя", N, true, gen), "a young creature");
        Eq("Багатоокого", In("Багатоокий", N, true, gen), "a neuter name on -ий");
        Eq("Дойоби", In("Дойоба", N, true, gen), "a neuter name on -а");
        Eq("реле", In("реле", N, false, gen), "реле never changes");
        // plural genitives
        Eq("труб", In("труби", P, false, gen), "a feminine plural ends bare");
        Eq("грибів", In("гриби", P, false, gen), "a masculine plural takes -ів");
        Eq("гаків", In("гаки", P, false, gen), "-ки after a vowel: masculine");
        Eq("пісень", In("пісні", P, false, gen), "a soft feminine plural");
        Eq("тіней", In("тіні", P, false, gen), "a feminine plural on a consonant");
        Eq("цінностей", In("цінності", P, false, gen), "-ості → -остей");
        Eq("полів", In("поля", P, false, gen), "a neuter plural on -я");
        Eq("ясел", In("ясла", P, false, gen), "е between two consonants");
        Eq("гір", In("гори", P, false, gen), "an alternation in the plural");
        Eq("Мімік і скаженоголовок", In("Мімік і скаженоголовок", P, false, gen), "a plural name with no plural head");
        Eq("глина, обшивка й тканина", In("глина, обшивка й тканина", P, false, gen), "a list stays");
        Eq("Злочин і кара", In("Злочин і кара", M, false, gen), "two things joined stay");
        Eq("купи брухту й глини", In("купа брухту й глини", F, false, gen), "but not a genitive joined");
        Eq("біонічних кистей", In("біонічні кисті", P, false, gen), "-сті → -стей");
        Eq("виповзка василіска", In("виповзок василіска", M, false, gen), "a vowel drops after two consonants");
        Eq("строку", In("строк", M, false, dat), "but not after тр");
        Eq("Кристалічності", In("Кристалічність", F, false, gen), "-ість → -ості");
        Eq("Кристалічністю", In("Кристалічність", F, false, ins), "but -істю");
        Eq("в’язки шумотрави", In("в’язка шумотрави", F, false, gen), "an adjective's look-alike before a genitive");
        Eq("механічного херувима-квітку", In("механічний херувим-квітка", M, true, acc), "each part in its own accusative");
        Eq("Повісті про страх", In("Повість про страх", F, false, gen), "повість → повісті");
        Eq("вартового Святилища", In("вартовий Святилища", M, true, acc), "an adjective before a proper genitive");
        Eq("іссахарі-стрільця", In("іссахарі-стрілець", M, true, acc), "-лець → -льця");
        AdjectiveLexicon.AddMasculinePluralStem("залишк");   // «залишків»
        Eq("залишків багаття", In("залишки багаття", P, false, gen), "a masculine plural on -ки");
        Eq("вас", UkrainianCases.You(acc), "the player");
        Eq("Mk I", In("Mk I", M, false, gen), "no Cyrillic: as it is");

        Eq("Упав", UkrainianForms.Capitalize("упав"), "capitalize");
        Eq("{{W|Упав}}", UkrainianForms.Capitalize("{{W|упав}}"), "capitalize inside markup");
        Eq("’Ять", UkrainianForms.Capitalize("’ять"), "capitalize skips punctuation");

        Eq("другий", UkrainianNumbers.OrdinalWord(2), "ordinal word");
        Eq("третій", UkrainianNumbers.OrdinalWord(3), "ordinal word, soft");
        Eq("двадцять перший", UkrainianNumbers.OrdinalWord(21), "compound ordinal");
        Eq("сороковий", UkrainianNumbers.OrdinalWord(40), "round ordinal");
        Eq("101-й", UkrainianNumbers.OrdinalWord(101), "a large ordinal in digits");
        Eq("12-й", UkrainianNumbers.OrdinalDigits(12), "ordinal in digits");
        Eq("12-го", UkrainianNumbers.DayOfMonth(12), "day of the month");
        Eq("один раз", UkrainianNumbers.Multiplicative(1), "once");
        Eq("двічі", UkrainianNumbers.Multiplicative(2), "twice");
        Eq("4 рази", UkrainianNumbers.Multiplicative(4), "four times");
        Eq("5 разів", UkrainianNumbers.Multiplicative(5), "five times");
        Eq("21 раз", UkrainianNumbers.Multiplicative(21), "twenty-one times");
        Eq("жодного разу", UkrainianNumbers.Multiplicative(0), "never");

        Eq("True", UkrainianNumbers.TryParseSavedTime("Friday, October 2, 2026 at 4:58:24 PM", out DateTime saved).ToString(), "parse the save time");
        Eq("2026-10-02 16:58:24", saved.ToString("yyyy-MM-dd HH:mm:ss"), "the parsed save time");
        Eq("п’ятниця, 2 жовтня 2026 р., 16:58:24",
           UkrainianNumbers.FormatSavedTime(saved, System.Globalization.CultureInfo.GetCultureInfo("uk-UA")), "the save time in Ukrainian");
        Eq("False", UkrainianNumbers.TryParseSavedTime("not a date", out _).ToString(), "garbage stays as it is");

        Eq("Feminine", UkrainianForms.GuessByEnding("Джоппа").ToString(), "a name in -а");
        Eq("Masculine", UkrainianForms.GuessByEnding("Туркатум").ToString(), "a name in a consonant");
        Eq("Plural", UkrainianForms.GuessByEnding("Карпати").ToString(), "a name in -и");
        Eq("", UkrainianForms.GuessByEnding("Ейн-Роґель").ToString(), "a soft sign does not tell");
        Eq("п’ятниця", UkrainianForms.CleanCultureText("пʼятниця"), "the typographic apostrophe");

        Eq("друже", UkrainianTerms.Get(KinTerm.FormalAddress, "male", false, false, "he"), "address a man");
        Eq("подруго", UkrainianTerms.Get(KinTerm.FormalAddress, "female", false, false, "she"), "address a woman");
        Eq("друже", UkrainianTerms.Get(KinTerm.FormalAddress, "nonspecific", false, true, "they"), "singular they is one person");
        Eq("друзі", UkrainianTerms.Get(KinTerm.FormalAddress, "plural", true, false, "they"), "a group");
        Eq("лане моя", UkrainianTerms.Get(KinTerm.FormalAddress, "hindren female", false, false, "she"), "hindren doe");
        Eq("сестро", UkrainianTerms.Get(KinTerm.Sibling, "female", false, false, "she"), "sister, vocative");
        Eq("родичу", UkrainianTerms.Get(KinTerm.Sibling, "elverson", false, false, "ey"), "sib for neopronouns");
        Eq("доню", UkrainianTerms.Get(KinTerm.Offspring, null, false, false, "she"), "a pronoun set without a gender name");
        Eq("особа", UkrainianTerms.Get(KinTerm.Person, "neuter", false, false, "it"), "a neutral person");

        Eq("Джопп", UkrainianWordTools.WordRoot("Джоппа"), "root of a name");
        Eq("мерехтлив", UkrainianWordTools.WordRoot("мерехтливий"), "root of an adjective");
        Eq("вод", UkrainianWordTools.WordRoot("вода"), "a short root keeps three letters");
        Eq("кров", UkrainianWordTools.WordRoot("кров"), "no ending");
        Eq("Туркатум", UkrainianWordTools.WordRoot("Туркатум"), "a consonant ending stays");
        Eq("сокира, камінь", string.Join(", ", UkrainianWordTools.MeaningfulWords("сокира з каменю").ConvertAll(w => w == "каменю" ? "камінь" : w)), "stop words drop out");
        Eq("і", string.Join(",", UkrainianWordTools.MeaningfulWords("і")), "nothing meaningful: every word");

        string[] mind = { "ваш розум", "розум (@)" };
        Eq("ваш розум", UkrainianForms.ForPlayerOrOther(true, mind), "the player's own wording");
        Eq("розум (@)", UkrainianForms.ForPlayerOrOther(false, mind), "anyone else, with the name");
        Eq("@", UkrainianForms.ForPlayerOrOther(false, new[] { "себе" }), "a lone form: anyone else gets the name");

        Console.WriteLine(failures == 0 ? "all grammar tests passed" : $"{failures} failure(s)");
        return failures == 0 ? 0 : 1;
    }
}
