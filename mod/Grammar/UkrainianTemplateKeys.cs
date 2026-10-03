using System.Collections.Generic;
using ConsoleLib.Console;
using XRL;
using XRL.Language;
using XRL.Rules;
using XRL.World;
using XRL.World.Text;
using XRL.World.Text.Attributes;
using XRL.World.Text.Delegates;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// Template keys whose English versions apply English morphology to our text, replaced while the game runs in
    /// Ukrainian (docs/research/localization-gaps.md, §3.1):
    ///   =x|nameStyle:TitleCase=        Ukrainian titles capitalise the first word only («Меч з каменю і вогню»)
    ///   =x|randomMeaningfulWord=       a word that carries meaning, by a Ukrainian stop list
    ///   =x|wordRoot=, =x|uk.stem=      a word without its ending, to build on («Джопп» + «град»)
    ///   =x|possessive= / |'s           nothing: «пащеклац's» is not Ukrainian
    ///   =zone.prosaic=                 the place as a noun phrase, no «the outskirts of»
    ///   =factionaddress:…=             not pluralised by English rules
    ///   =x.disguise.name=              without «a»
    ///   =x.descriptiveCategory=        not pluralised by English rules
    ///   =x.formalAddressTerm= and the other address and kinship terms, by gender (UkrainianTerms)
    /// </summary>
    [HasVariableReplacer(Lang = "uk")]
    public static class UkrainianTemplateKeys
    {
        // ---- names and words ----

        [VariablePostProcessor(new string[] { "nameStyle" }, Override = true)]
        public static void NameStyle(VariableContext Context, string Format = null)
        {
            if (string.IsNullOrEmpty(Format) && Context.Parameters.Count > 0) Format = Context.Parameters[0];
            string value = Context.Value.ToString();
            string text;
            switch (Format)
            {
                case "TitleCase":
                case "Capitalized": text = UkrainianForms.Capitalize(value); break;
                case "AllCaps": text = ColorUtility.ToUpperExceptFormatting(value); break;
                case "LowerCase": text = ColorUtility.ToLowerExceptFormatting(value); break;
                case "SpacesToHyphens": text = ColorUtility.ReplaceExceptFormatting(value, ' ', '-'); break;
                default: return;
            }
            Set(Context, value, text);
        }

        [VariablePostProcessor(new string[] { "randomMeaningfulWord" }, Override = true)]
        public static void RandomMeaningfulWord(VariableContext Context)
        {
            string value = Context.Value.ToString();
            Set(Context, value, PickMeaningful(value));
        }

        [VariablePostProcessor(new string[] { "wordRoot" }, Override = true)]
        public static void WordRoot(VariableContext Context)
        {
            string value = Context.Value.ToString();
            Set(Context, value, UkrainianWordTools.WordRoot(PickMeaningful(UkrainianForms.StripMarkup(value))));
        }

        /// <summary>=liquid|uk.stem=о=player.siblingTerm= → «водобрате»: the value without its ending.</summary>
        [VariablePostProcessor(new string[] { "uk.stem" })]
        public static void Stem(VariableContext Context)
        {
            string value = Context.Value.ToString();
            Set(Context, value, UkrainianWordTools.WordRoot(UkrainianForms.StripMarkup(value)).ToLowerInvariant());
        }

        [VariablePostProcessor(new string[] { "possessive", "makePossessive", "'s" }, Override = true)]
        public static void Possessive(VariableContext Context)
        {
        }

        static string PickMeaningful(string phrase)
        {
            List<string> words = UkrainianWordTools.MeaningfulWords(phrase);
            return words.Count == 0 ? phrase : words[Stat.Random(0, words.Count - 1)];
        }

        static void Set(VariableContext Context, string old, string value)
        {
            if (value == old) return;
            Context.Value.Clear();
            Context.Value.Append(value);
        }

        // ---- places ----

        [VariableReplacer(new string[] { "zone.prosaic" }, Override = true)]
        public static string ZoneProsaic(VariableContext Context)
        {
            Zone zone = The.Player?.CurrentZone;
            if (zone == null) return "";
            if (zone.HasProperName) return zone.DisplayName;
            if (!string.IsNullOrEmpty(zone.NameContext)) return zone.NameContext;
            return zone.GetTerrainObject()?.ShortDisplayNameStripped ?? "";
        }

        // ---- people ----

        [VariableReplacer(new string[] { "factionaddress" }, Override = true)]
        public static string FactionAddress(VariableContext Context)
        {
            string text = Context.Default;
            if (Context.Parameters.Count == 0) return text;
            string faction = Context.Parameters[0];
            text = The.Game?.PlayerReputation.GetFactionRank(faction);
            bool formal = false;
            if (Context.Parameters.Count > 1)
            {
                Context.Parameters.Remove("singular");
                formal = Context.Parameters.Remove("formal");
                if (Context.Parameters.Count > 1 && string.IsNullOrEmpty(text)) text = Context.Parameters[1];
            }
            if (string.IsNullOrEmpty(text)) text = Faction.GetDefaultAddress(faction);
            if (string.IsNullOrEmpty(text)) text = Term(formal ? KinTerm.FormalAddress : KinTerm.Person, The.Player);
            // English pluralised the address for a plural player; Ukrainian ranks have no rule for it
            return text;
        }

        [VariableReplacer(new string[] { "disguise.name" }, Capitalization = true, Override = true)]
        public static void DisguiseName(VariableContext Context, GameObjectBlueprint BP, GameObject Object)
        {
            Context.Value.Append(BP.GetPartParameter("Render", "DisplayName", XRL.World.Effects.Disguised.DefaultDisguiseName));
            if (Context.Capitalize) Context.Value.InitUpper();
        }

        [VariableReplacer(new string[] { "descriptiveCategory" }, Capitalization = true, Override = true)]
        public static void DescriptiveCategory(VariableContext Context, GameObject Item)
        {
            Context.Value.Append(Item.GetDescriptiveCategory());
            if (Context.Capitalize) Context.Value.InitUpper();
        }

        // ---- address and kinship terms ----

        [VariableReplacer(new string[] { "formalAddressTerm" }, Capitalization = true, Override = true)]
        public static string FormalAddressTerm(VariableContext Context, GameObject Object) => Term(Context, KinTerm.FormalAddress, Object);

        [VariableReplacer(new string[] { "formalAddressTerm" }, Capitalization = true, Override = true)]
        public static string FormalAddressTerm(VariableContext Context, GenderedNoun Noun) => Term(Context, KinTerm.FormalAddress, Noun);

        [VariableReplacer(new string[] { "siblingTerm" }, Capitalization = true, Override = true)]
        public static string SiblingTerm(VariableContext Context, GameObject Object) => Term(Context, KinTerm.Sibling, Object);

        [VariableReplacer(new string[] { "siblingTerm" }, Capitalization = true, Override = true)]
        public static string SiblingTerm(VariableContext Context, GenderedNoun Noun) => Term(Context, KinTerm.Sibling, Noun);

        [VariableReplacer(new string[] { "offspringTerm" }, Capitalization = true, Override = true)]
        public static string OffspringTerm(VariableContext Context, GameObject Object) => Term(Context, KinTerm.Offspring, Object);

        [VariableReplacer(new string[] { "offspringTerm" }, Capitalization = true, Override = true)]
        public static string OffspringTerm(VariableContext Context, GenderedNoun Noun) => Term(Context, KinTerm.Offspring, Noun);

        [VariableReplacer(new string[] { "personTerm" }, Capitalization = true, Override = true)]
        public static string PersonTerm(VariableContext Context, GameObject Object) => Term(Context, KinTerm.Person, Object);

        [VariableReplacer(new string[] { "personTerm" }, Capitalization = true, Override = true)]
        public static string PersonTerm(VariableContext Context, GenderedNoun Noun) => Term(Context, KinTerm.Person, Noun);

        [VariableReplacer(new string[] { "immaturePersonTerm" }, Capitalization = true, Override = true)]
        public static string ImmaturePersonTerm(VariableContext Context, GameObject Object) => Term(Context, KinTerm.ImmaturePerson, Object);

        [VariableReplacer(new string[] { "immaturePersonTerm" }, Capitalization = true, Override = true)]
        public static string ImmaturePersonTerm(VariableContext Context, GenderedNoun Noun) => Term(Context, KinTerm.ImmaturePerson, Noun);

        [VariableReplacer(new string[] { "parentTerm" }, Capitalization = true, Override = true)]
        public static string ParentTerm(VariableContext Context, GameObject Object) => Term(Context, KinTerm.Parent, Object);

        [VariableReplacer(new string[] { "parentTerm" }, Capitalization = true, Override = true)]
        public static string ParentTerm(VariableContext Context, GenderedNoun Noun) => Term(Context, KinTerm.Parent, Noun);

        static string Term(VariableContext Context, KinTerm term, GameObject Object)
        {
            string text = Term(term, Object);
            return Context.Capitalize ? UkrainianForms.Capitalize(text) : text;
        }

        static string Term(VariableContext Context, KinTerm term, GenderedNoun Noun)
        {
            IPronounProvider pronouns = Noun.Pronouns;
            string text = pronouns is Gender gender
                ? UkrainianTerms.Get(term, gender.Name, gender.Plural, gender.PseudoPlural, gender.Subjective)
                : UkrainianTerms.Get(term, null, pronouns?.Plural ?? false, pronouns?.PseudoPlural ?? false, pronouns?.Subjective);
            return Context.Capitalize ? UkrainianForms.Capitalize(text) : text;
        }

        // the person's own gender, not the «ви» pronoun set the player speaks through
        static string Term(KinTerm term, GameObject Object)
        {
            Gender gender = Object?.GetGender();
            if (gender == null) return UkrainianTerms.Get(term, null, false, false, null);
            return UkrainianTerms.Get(term, gender.Name, gender.Plural, gender.PseudoPlural, gender.Subjective);
        }
    }
}
