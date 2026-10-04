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
        Eq("Feminine", CodeWords.GenderOf("Owl").ToString(), "gender by the English word");
        Eq("Masculine", CodeWords.GenderOf("Орел").ToString(), "gender by the Ukrainian word");

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
