// Address and kinship terms (=player.formalAddressTerm=, =pronouns.siblingTerm=…) in Ukrainian. The game takes them
// from Genders.xml or, for the player and the neuter genders, from English defaults in its code («friend», «sib»).
// Our texts use the address terms when speaking to someone, so those are vocative («Живіть і пийте, друже»), and
// the descriptive ones nominative. Free of game types, so tools/grammar-tests can run it.
namespace CavesOfQudUA.Grammar
{
    public enum KinTerm { Person, ImmaturePerson, FormalAddress, Offspring, Sibling, Parent }

    public static class UkrainianTerms
    {
        // classes: 0 man, 1 woman, 2 neutral (it, they of one person, neopronouns), 3 group, 4 men, 5 women,
        // 6 hindren buck, 7 hindren doe
        static readonly string[][] Table =
        {
            /* Person         */ new[] { "чоловік", "жінка", "особа", "люди", "чоловіки", "жінки", "олень", "лань" },
            /* ImmaturePerson */ new[] { "хлопець", "дівчина", "дитина", "діти", "хлопці", "дівчата", "оленя", "оленя" },
            /* FormalAddress  */ new[] { "друже", "подруго", "друже", "друзі", "друзі", "подруги", "оленю", "лане моя" },
            /* Offspring      */ new[] { "сину", "доню", "дитино", "діти", "сини", "доньки", "сину", "доню" },
            /* Sibling        */ new[] { "брате", "сестро", "родичу", "родичі", "брати", "сестри", "брате", "сестро" },
            /* Parent         */ new[] { "батько", "мати", "предок", "предки", "батьки", "матері", "батько", "мати" },
        };

        /// <summary>
        /// The term for a gender as the game describes it: its name (Genders.xml), whether it is a real plural (a
        /// group) or only grammatically plural (singular they), and its subjective pronoun.
        /// </summary>
        public static string Get(KinTerm term, string genderName, bool plural, bool pseudoPlural, string subjective)
        {
            return Table[(int)term][Class(genderName, plural, pseudoPlural, subjective)];
        }

        static int Class(string name, bool plural, bool pseudoPlural, string subjective)
        {
            switch (name)
            {
                case "male": return 0;
                case "female": return 1;
                case "males": return 4;
                case "females": return 5;
                case "hindren male": return 6;
                case "hindren female": return 7;
            }
            if (plural && !pseudoPlural) return 3;
            switch (subjective)
            {
                case "he": return 0;
                case "she": return 1;
            }
            return 2;
        }
    }
}
