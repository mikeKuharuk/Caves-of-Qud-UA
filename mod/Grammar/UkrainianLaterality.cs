using System.Collections.Generic;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// A body part's sides in Ukrainian: «ліва рука», «верхній правий ріг», «права задня нога». The game writes them in
    /// English (XRL.World.Capabilities.Laterality: «left arm», «right hindleg»); here the adjectives agree with the noun,
    /// in the game's order (inner/outer, upper/lower, right/left, inside/outside, mid/fore/hind), and nothing is joined
    /// into the noun as «fore» is in «foreleg».
    /// </summary>
    public static class UkrainianLaterality
    {
        // the game's laterality bits (Laterality.LEFT…OUTER)
        const int Left = 1, Right = 2, Upper = 4, Lower = 8, Fore = 16, Mid = 32, Hind = 64, Inside = 128,
                  Outside = 256, Inner = 512, Outer = 1024;

        static readonly string[] InnerForms = { "внутрішній", "внутрішня", "внутрішнє", "внутрішні" };
        static readonly string[] OuterForms = { "зовнішній", "зовнішня", "зовнішнє", "зовнішні" };

        // the bits a word stands for, in the order the game writes them; forms masculine, feminine, neuter, plural
        static readonly (int Bits, string[] Forms)[] Words =
        {
            (Inner, InnerForms),
            (Outer, OuterForms),
            (Upper, new[] { "верхній", "верхня", "верхнє", "верхні" }),
            (Lower, new[] { "нижній", "нижня", "нижнє", "нижні" }),
            (Right, new[] { "правий", "права", "праве", "праві" }),
            (Left, new[] { "лівий", "ліва", "ліве", "ліві" }),
            (Inside, InnerForms),      // a door's knobs: «внутрішня ручка»
            (Outside, OuterForms),
            (Mid | Fore, new[] { "середньо-передній", "середньо-передня", "середньо-переднє", "середньо-передні" }),
            (Mid | Hind, new[] { "середньо-задній", "середньо-задня", "середньо-заднє", "середньо-задні" }),
            (Mid, new[] { "середній", "середня", "середнє", "середні" }),
            (Fore, new[] { "передній", "передня", "переднє", "передні" }),
            (Hind, new[] { "задній", "задня", "заднє", "задні" }),
        };

        static int Index(UkGender gender)
        {
            switch (gender)
            {
                case UkGender.Feminine: return 1;
                case UkGender.Neuter: return 2;
                case UkGender.Plural: return 3;
                default: return 0;
            }
        }

        /// <summary>The adjectives for the laterality, in the noun's gender: «ліва», «права задня».</summary>
        public static string Adjectives(int laterality, UkGender gender)
        {
            var words = new List<string>();
            int left = laterality;
            foreach (var w in Words)
            {
                if ((left & w.Bits) != w.Bits) continue;
                words.Add(w.Forms[Index(gender)]);
                left &= ~w.Bits;
            }
            return string.Join(" ", words);
        }

        /// <summary>
        /// The noun with its laterality: «ліва рука»; capitalized for the equipment screen («Ліва рука»). A noun with no
        /// laterality comes back as it is.
        /// </summary>
        public static string With(string noun, int laterality, UkGender gender, bool capitalized)
        {
            string adjectives = Adjectives(laterality, gender);
            if (adjectives.Length == 0) return noun;
            string text = noun == null ? adjectives : adjectives + " " + LowerFirst(noun);
            return capitalized ? UkrainianForms.Capitalize(text) : text;
        }

        /// <summary>
        /// The noun without the laterality adjectives at its start (any gender's forms of the laterality's words), as
        /// the game strips its English ones before it puts on new ones.
        /// </summary>
        public static string Strip(string text, int laterality, bool capitalized)
        {
            if (string.IsNullOrEmpty(text)) return text;
            var forms = new HashSet<string>();
            int left = laterality;
            foreach (var w in Words)
            {
                if ((left & w.Bits) != w.Bits) continue;
                foreach (string f in w.Forms) forms.Add(f);
                left &= ~w.Bits;
            }
            string[] words = text.Split(' ');
            int i = 0;
            while (i < words.Length - 1 && forms.Contains(words[i].ToLowerInvariant())) i++;
            if (i == 0) return text;
            string rest = string.Join(" ", words, i, words.Length - i);
            return capitalized ? UkrainianForms.Capitalize(rest) : rest;
        }

        /// <summary>«друга ліва рука»: an ordinal agreed with the noun, before it, which then starts in lower case.</summary>
        public static string WithOrdinal(long position, string noun, UkGender gender, bool capitalized)
        {
            string ordinal = UkrainianForms.InflectRegular(UkrainianNumbers.OrdinalWord(position), gender);
            string text = ordinal + " " + LowerFirst(noun);
            return capitalized ? UkrainianForms.Capitalize(text) : text;
        }

        static string LowerFirst(string text)
        {
            if (string.IsNullOrEmpty(text) || !char.IsUpper(text[0])) return text;
            return char.ToLowerInvariant(text[0]) + text.Substring(1);
        }
    }
}
