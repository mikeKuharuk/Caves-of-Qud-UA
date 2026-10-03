using System;
using XRL.Language;
using XRL.World.Text.Attributes;
using XRL.World.Text.Delegates;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// Dates in Ukrainian.
    ///   =day=, =n.displayDate=     the day of the Qud month: «12-го Туум Ут»; the 15th keeps the table's «Іди»
    ///   =longDate= and the like    real-world dates in the Ukrainian culture, with the apostrophe our text uses
    ///   =saveTime|uk.date=         the save list's «Friday, October 2, 2026 at 4:58:24 PM», which the game stores in
    ///                              English and sorts by, shown as «п’ятниця, 2 жовтня 2026 р., 16:58:24»
    /// </summary>
    [HasVariableReplacer(Lang = "uk")]
    public static class UkrainianCalendar
    {
        [VariableReplacer("displayDate", Override = true)]
        public static void DisplayDate(VariableContext Context, int DayNumber)
        {
            Context.Value.Append(DayNumber == 15 ? Strings._S("Calendar Day 15", "Ides") : UkrainianNumbers.DayOfMonth(DayNumber));
        }

        [VariableReplacer("longDate", Override = true)]
        public static void LongDate(VariableContext Context)
        {
            Context.Value.Append(Format(DateTime.Now, "D"));
        }

        [VariableReplacer("longTime", Override = true)]
        public static void LongTime(VariableContext Context)
        {
            Context.Value.Append(Format(DateTime.Now, "T"));
        }

        [VariableReplacer("fullDate", Override = true)]
        public static void FullDate(VariableContext Context)
        {
            Context.Value.Append(Format(DateTime.Now, "f"));
        }

        [VariableReplacer("fullDate", Override = true)]
        public static void FullDate(VariableContext Context, DateTime Time)
        {
            Context.Value.Append(Format(Time, "f"));
        }

        /// <summary>A date the game wrote in English («Friday, October 2, 2026 at 4:58:24 PM»), in Ukrainian.</summary>
        [VariablePostProcessor(new string[] { "uk.date" })]
        public static void Date(VariableContext Context)
        {
            string value = Context.Value.ToString();
            if (!UkrainianNumbers.TryParseSavedTime(value, out DateTime time)) return;
            Context.Value.Clear();
            Context.Value.Append(UkrainianNumbers.FormatSavedTime(time, Translator.CultureInfo));
        }

        static string Format(DateTime time, string format)
        {
            return UkrainianForms.CleanCultureText(time.ToString(format, Translator.CultureInfo));
        }
    }
}
