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

        string[] fell = { "упав", "упала", "упало", "упали" };
        Eq("упав", UkrainianForms.ByGender(UkGender.Masculine, fell), "masculine");
        Eq("упала", UkrainianForms.ByGender(UkGender.Feminine, fell), "feminine");
        Eq("упало", UkrainianForms.ByGender(UkGender.Neuter, fell), "neuter");
        Eq("упали", UkrainianForms.ByGender(UkGender.Plural, fell), "plural");
        Eq("готовий", UkrainianForms.ByGender(UkGender.Neuter, new[] { "готовий", "готова" }), "a missing neuter takes the masculine");
        Eq("готова", UkrainianForms.ByGender(UkGender.Plural, new[] { "готовий", "готова" }), "a missing plural takes the last form");

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

        Eq("Упав", UkrainianForms.Capitalize("упав"), "capitalize");
        Eq("{{W|Упав}}", UkrainianForms.Capitalize("{{W|упав}}"), "capitalize inside markup");
        Eq("’Ять", UkrainianForms.Capitalize("’ять"), "capitalize skips punctuation");

        Console.WriteLine(failures == 0 ? "all grammar tests passed" : $"{failures} failure(s)");
        return failures == 0 ? 0 : 1;
    }
}
