using System.Collections.Generic;
using System.Reflection;
using CavesOfQudUA.Grammar;
using HarmonyLib;
using Qud.UI;
using XRL.Messages;
using XRL.UI;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// Popups, failure messages and message-log lines the game's C# writes in English (607 popup and 335 log places
    /// in the code, docs/research/localization-gaps.md §2): «You receive X!», «You cannot examine things while you are
    /// confused.». They pass a few sinks, where the text goes through the Text code table (CodeText): exactly, by
    /// pattern, or line by line. Text the string tables already translated has no English and passes at once.
    /// </summary>
    [HarmonyPatch(typeof(Popup), nameof(Popup.ShowBlock))]
    static class ShowBlockPatch
    {
        // before Markup.Transform, so the keys' {{X|…}} markup still matches; it also covers Show, ShowFail and Fail
        static void Prefix(ref string Message, ref string Title)
        {
            if (!Uk.Active) return;
            Message = CodeText.Translate("Text", Message);
            Title = CodeText.Translate("Text", Title);
        }
    }

    /// <summary>The modern popup every other popup ends in: yes/no questions, prompts, option lists.</summary>
    [HarmonyPatch(typeof(PopupMessage), nameof(PopupMessage.ShowPopup))]
    static class ShowPopupPatch
    {
        static bool Prepare() => !Uk.OutsideUnity;   // a Unity component: only the game can patch it

        static void Prefix(ref string message, ref string title, ref string contextTitle, List<QudMenuItem> buttons,
                           List<QudMenuItem> items)
        {
            if (!Uk.Active) return;
            message = CodeText.Translate("Text", message);
            title = CodeText.Translate("Text", title);
            contextTitle = CodeText.Translate("Text", contextTitle);
            Items(buttons);
            Items(items);
        }

        static void Items(List<QudMenuItem> list)
        {
            if (list == null) return;
            for (int i = 0; i < list.Count; i++)
            {
                QudMenuItem item = list[i];
                string text = CodeText.Translate("Text", item.text);
                if (text == item.text) continue;
                item.text = text;
                list[i] = item;
            }
        }
    }

    /// <summary>Option lists, the classic UI included: the title, the intro and each option.</summary>
    [HarmonyPatch]
    static class PickOptionPatch
    {
        static IEnumerable<MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(Popup), nameof(Popup.PickOption));
            yield return AccessTools.Method(typeof(Popup), nameof(Popup.PickOptionAsync));
        }

        static void Prefix(ref string Title, ref string Intro, ref IReadOnlyList<string> Options)
        {
            if (!Uk.Active) return;
            Title = CodeText.Translate("Text", Title);
            Intro = CodeText.Translate("Text", Intro);
            if (Options == null) return;
            List<string> translated = null;
            for (int i = 0; i < Options.Count; i++)
            {
                string text = CodeText.Translate("Text", Options[i]);
                if (text == Options[i] && translated == null) continue;
                if (translated == null)
                {
                    translated = new List<string>(Options.Count);
                    for (int j = 0; j < i; j++) translated.Add(Options[j]);
                }
                translated.Add(text);
            }
            if (translated != null) Options = translated;
        }
    }

    /// <summary>
    /// The message log's title. The window sets it once, in Init, while the game starts up: before the mods load, so
    /// the string table has no Ukrainian yet («String table miss … Message Log Title» in Player.log) and the title
    /// stays «Message log». GameInit runs at the start of every game, new or loaded; set the title again there.
    /// </summary>
    [HarmonyPatch(typeof(MessageLogWindow), nameof(MessageLogWindow.GameInit))]
    static class MessageLogTitlePatch
    {
        static void Postfix()
        {
            if (!Uk.Active) return;
            SingletonWindowBase<MessageLogWindow>.instance?.headerText?.SetText(
                XRL.Language.Strings._S("Message Log Title", "Message log"));
        }
    }

    /// <summary>
    /// The journal's tabs. Their names are English constants (JournalScreen.STR_*) that the code also compares, so they
    /// stay English inside; what the player reads comes from the Words code table: the journal's title
    /// (GetTabDisplayName) and the tab button's tooltip (FilterBarCategoryButton: the journal's tabs show an icon and
    /// name themselves in the tooltip).
    /// </summary>
    [HarmonyPatch(typeof(JournalScreen), nameof(JournalScreen.GetTabDisplayName))]
    static class JournalTabNamePatch
    {
        static void Postfix(ref string __result)
        {
            if (!Uk.Active) return;
            __result = CodeTables.Get("Words", __result) ?? __result;
        }
    }

    /// <summary>
    /// And the inventory filter's first button: its label is a constant of the button (categoryTextMap: «*All» →
    /// «ALL»), from the Words table too, and so is its tooltip, the bare «*All».
    /// </summary>
    [HarmonyPatch(typeof(FilterBarCategoryButton), nameof(FilterBarCategoryButton.SetCategory))]
    static class CategoryButtonTooltipPatch
    {
        static void Postfix(FilterBarCategoryButton __instance, string category, string tooltip)
        {
            if (!Uk.Active || category == null) return;
            if (FilterBarCategoryButton.categoryTextMap.TryGetValue(category, out string label))
            {
                string shown = CodeTables.Get("Words", label);
                if (shown == null) return;
                __instance.text?.SetText(shown);
                if (tooltip == null) SetTooltip(__instance, shown);
                return;
            }
            if (tooltip != null) return;
            string word = CodeTables.Get("Words", category);
            if (word != null) SetTooltip(__instance, word);
        }

        static void SetTooltip(FilterBarCategoryButton button, string text)
        {
            button.Tooltip = text;
            button.tooltipText?.SetText(text);
        }
    }

    /// <summary>
    /// Labels a Unity prefab carries, which no code or table holds: the load screen's «delete» button and «Mods
    /// Differ» mark (SaveManagementRow). A text under them whose text is a Words key gets its Ukrainian; any markup
    /// around it stays. Not seen in the game yet: if the prefab's label is no UITextSkin, nothing changes.
    /// </summary>
    [HarmonyPatch(typeof(SaveManagementRow), nameof(SaveManagementRow.setData))]
    static class SaveRowLabelsPatch
    {
        static bool Prepare() => !Uk.OutsideUnity;   // Unity components: only the game can patch them

        static void Postfix(SaveManagementRow __instance)
        {
            if (!Uk.Active) return;
            try
            {
                PrefabLabels(__instance.deleteButton?.gameObject);
                PrefabLabels(__instance.modsDiffer);
            }
            catch (System.Exception) { }   // a label left English must never break the load screen
        }

        static void PrefabLabels(UnityEngine.GameObject root)
        {
            if (root == null) return;
            foreach (UITextSkin skin in root.GetComponentsInChildren<UITextSkin>(true))
            {
                string plain = UkrainianForms.StripMarkup(skin.text ?? "").Trim();
                string word = plain.Length > 0 ? CodeTables.Get("Words", plain) : null;
                if (word != null) skin.SetText(skin.text.Replace(plain, word));
            }
        }
    }

    /// <summary>The message log.</summary>
    [HarmonyPatch]
    static class AddPlayerMessagePatch
    {
        static IEnumerable<MethodBase> TargetMethods()
        {
            yield return AccessTools.Method(typeof(MessageQueue), nameof(MessageQueue.AddPlayerMessage),
                                            new[] { typeof(string), typeof(string), typeof(bool) });
            yield return AccessTools.Method(typeof(MessageQueue), nameof(MessageQueue.AddPlayerMessage),
                                            new[] { typeof(string), typeof(char), typeof(bool) });
        }

        static void Prefix(ref string Message)
        {
            if (!Uk.Active) return;
            Message = CodeText.Translate("Text", Message);
        }
    }
}
