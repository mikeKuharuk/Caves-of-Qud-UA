using System.Collections.Generic;
using XRL.Language;

namespace CavesOfQudUA.Grammar
{
    /// <summary>
    /// The language provider for Ukrainian. It keeps the English behaviour of TranslatorBase except where Ukrainian
    /// differs; the rest (cases, adjective agreement, numbers in words, culture) comes in later steps of
    /// docs/grammar.md and needs a check in the game first.
    /// </summary>
    [LanguageProvider("uk")]
    public class UkrainianProvider : TranslatorBase
    {
        /// <summary>Ukrainian has no articles.</summary>
        public override string DefiniteArticle(DefiniteArticleParams Params)
        {
            return "";
        }

        public override string IndefiniteArticle(IndefiniteArticleParams Params)
        {
            return "";
        }

        /// <summary>«А, Б і В»: no comma before the conjunction (the separators themselves come from the string table).</summary>
        public override string MakeAndList(IReadOnlyList<string> List, MakeAndListParams Params = default)
        {
            return base.MakeAndList(List, new MakeAndListParams(false));
        }

        public override string MakeOrList(IReadOnlyList<string> List, MakeOrListParams Params = default)
        {
            return base.MakeOrList(List, new MakeOrListParams(false));
        }
    }
}
