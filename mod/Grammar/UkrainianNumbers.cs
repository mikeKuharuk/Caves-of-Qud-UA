// Ukrainian numerals for the provider (UkrainianProvider): ordinals in words and in digits, the day of the month and
// «N разів». Free of game types, so tools/grammar-tests can run it.
namespace CavesOfQudUA.Grammar
{
    public static class UkrainianNumbers
    {
        static readonly string[] Units =
        {
            "нульовий", "перший", "другий", "третій", "четвертий", "п’ятий", "шостий", "сьомий", "восьмий", "дев’ятий",
            "десятий", "одинадцятий", "дванадцятий", "тринадцятий", "чотирнадцятий", "п’ятнадцятий", "шістнадцятий",
            "сімнадцятий", "вісімнадцятий", "дев’ятнадцятий",
        };
        static readonly string[] TensOrdinal =
        {
            "", "", "двадцятий", "тридцятий", "сороковий", "п’ятдесятий", "шістдесятий", "сімдесятий", "вісімдесятий",
            "дев’яностий",
        };
        static readonly string[] TensCardinal =
        {
            "", "", "двадцять", "тридцять", "сорок", "п’ятдесят", "шістдесят", "сімдесят", "вісімдесят", "дев’яносто",
        };

        /// <summary>
        /// An ordinal in words, masculine nominative: 2 → «другий», 21 → «двадцять перший». The game asks for these
        /// for the second of two like body parts («друга ліва рука» once agreed). From 100 on, digits: «101-й».
        /// </summary>
        public static string OrdinalWord(long number)
        {
            if (number < 0 || number >= 100) return OrdinalDigits(number);
            if (number < 20) return Units[number];
            long tens = number / 10, unit = number % 10;
            return unit == 0 ? TensOrdinal[tens] : TensCardinal[tens] + " " + Units[unit];
        }

        /// <summary>An ordinal in digits, masculine nominative: «12-й». |uk.agree turns it into 12-та, 12-те, 12-ті.</summary>
        public static string OrdinalDigits(long number)
        {
            return number + "-й";
        }

        /// <summary>The day of the month as Ukrainians write a date: «12-го» (Туум Ут).</summary>
        public static string DayOfMonth(long day)
        {
            return day + "-го";
        }

        /// <summary>How many times: «жодного разу», «один раз», «двічі», «тричі», «4 рази», «5 разів», «21 раз».</summary>
        public static string Multiplicative(long number)
        {
            switch (number)
            {
                case 0: return "жодного разу";
                case 1: return "один раз";
                case 2: return "двічі";
                case 3: return "тричі";
            }
            return number + " " + UkrainianForms.ByNumber(number, new[] { "раз", "рази", "разів" });
        }

        /// <summary>
        /// The save time as the game stores it: ToLongDateString() + " at " + ToLongTimeString() in the thread's
        /// culture, en-US or invariant («Friday, October 2, 2026 at 4:58:24 PM»). The save list sorts by this text,
        /// so it stays stored as it is and only the display changes.
        /// </summary>
        public static bool TryParseSavedTime(string text, out System.DateTime time)
        {
            time = default;
            if (string.IsNullOrEmpty(text)) return false;
            string joined = text.Replace(" at ", " ");
            var cultures = new[] { System.Globalization.CultureInfo.GetCultureInfo("en-US"), System.Globalization.CultureInfo.InvariantCulture };
            foreach (var culture in cultures)
                if (System.DateTime.TryParse(joined, culture, System.Globalization.DateTimeStyles.AllowWhiteSpaces, out time))
                    return true;
            return false;
        }

        /// <summary>«п’ятниця, 2 жовтня 2026 р., 16:58:24» in the given (Ukrainian) culture.</summary>
        public static string FormatSavedTime(System.DateTime time, System.Globalization.CultureInfo culture)
        {
            return UkrainianForms.CleanCultureText(time.ToString("D", culture) + ", " + time.ToString("T", culture));
        }
    }
}
