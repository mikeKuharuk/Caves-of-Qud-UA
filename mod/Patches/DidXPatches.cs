using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using XRL;
using XRL.World;
using XRL.World.Capabilities;

namespace CavesOfQudUA.Patches
{
    /// <summary>
    /// The narration the game builds itself, with English grammar, from a verb and a few words: Messaging.XDidY,
    /// XDidYToZ and WDidXToYWithZ (DidX, DidXToY, DidXToYWithZ on parts), 472 places in the code: «X dies!», «You
    /// begin healing.». The game objects are still at hand there, so the Ukrainian is a template of our grammar
    /// (=subject.Name= =subject.v:помирає:помираєте:помирають=!) from the DidX code table.
    ///
    /// How: a prefix on each of the three remembers the call (who, verb, prepositions, objects, extra words, end
    /// mark); each of them ends in exactly one Messaging.HandleMessage, where a prefix swaps the English text for the
    /// rendered template. Visibility, popups and colours stay the game's. No template: the English stays (and is
    /// logged as a miss with its key).
    /// </summary>
    static class DidX
    {
        sealed class Call
        {
            public string Kind, Verb, Prep, IPrep, Extra, End, Color, SubjectOverride;
            public GameObject Actor, Object, Indirect, Owner;
            public bool Done;
        }

        [ThreadStatic] static List<Call> calls;

        public static void Push(string kind, GameObject actor, string verb, string prep, GameObject obj, string iprep,
                                GameObject indirect, string extra, string end, string subjectOverride, string color,
                                GameObject owner)
        {
            (calls ?? (calls = new List<Call>())).Add(new Call
            {
                Kind = kind, Actor = actor, Verb = verb, Prep = prep, Object = obj, IPrep = iprep, Indirect = indirect,
                Extra = extra, End = end, SubjectOverride = subjectOverride, Color = color, Owner = owner,
            });
        }

        public static void Pop()
        {
            if (calls != null && calls.Count > 0) calls.RemoveAt(calls.Count - 1);
        }

        /// <summary>The key the DidX table uses (tools/qudtr/codescan.py, didx_key).</summary>
        public static string Key(string kind, string verb, string prep, string iprep, string extra, string end)
        {
            return string.Join("|", kind, verb ?? "", prep ?? "", iprep ?? "", extra ?? "", end ?? ".");
        }

        /// <summary>
        /// The template for a call: the one keyed by its own verb; else, for a verb the game's data gives (a projectile's
        /// «whiz», a device's «beep»), the message's «*» template with the verb's forms from the Verbs table where {v}
        /// stands. Null when neither is there (logged as a miss: the call's own key, or the verb the table lacks).
        /// </summary>
        public static string Template(string kind, string verb, string prep, string iprep, string extra, string end)
        {
            string key = Key(kind, verb, prep, iprep, extra, end);
            string own = CodeText.Peek("DidX", key);
            if (own != null) return own;
            string general = CodeText.Peek("DidX", Key(kind, "*", prep, iprep, extra, end));
            if (general == null)
            {
                CodeText.Lookup("DidX", key);
                return null;
            }
            string forms = CodeText.Lookup("Verbs", verb);
            return forms == null ? null : general.Replace("{v}", "=subject.v:" + forms + "=");
        }

        /// <summary>The message of the call in progress, in Ukrainian, if its template exists.</summary>
        public static void Render(ref string message)
        {
            if (calls == null || calls.Count == 0 || !Uk.Active) return;
            Call call = calls[calls.Count - 1];
            if (call.Done || call.SubjectOverride != null || string.IsNullOrEmpty(call.Verb)) return;
            call.Done = true;
            string template = Template(call.Kind, call.Verb, call.Prep, call.IPrep, call.Extra, call.End);
            if (template == null) return;
            var builder = template.StartReplace();
            if (call.Actor != null) builder.SetSubject(call.Actor);
            if (call.Object != null) builder.SetObject(call.Object);
            if (call.Indirect != null) builder.SetArgument("indirect", call.Indirect);
            if (call.Owner != null) builder.SetArgument("owner", call.Owner);
            string text = builder.ToString();
            // XDidY wraps its whole text in the colour; the other two pass the colour to HandleMessage instead
            if (call.Kind == "X" && !string.IsNullOrEmpty(call.Color)) text = "{{" + call.Color + "|" + text + "}}";
            message = text;
        }
    }

    [HarmonyPatch(typeof(Messaging), nameof(Messaging.XDidY))]
    static class XDidYPatch
    {
        static void Prefix(GameObject Actor, string Verb, string Extra, string EndMark, string SubjectOverride, string Color,
                           GameObject SubjectPossessedBy)
        {
            DidX.Push("X", Actor, Verb, null, null, null, null, Extra, EndMark, SubjectOverride, Color, SubjectPossessedBy);
        }

        static Exception Finalizer(Exception __exception)
        {
            DidX.Pop();
            return __exception;
        }
    }

    [HarmonyPatch(typeof(Messaging), nameof(Messaging.XDidYToZ))]
    static class XDidYToZPatch
    {
        static void Prefix(GameObject Actor, string Verb, string Preposition, GameObject Object, string Extra, string EndMark,
                           string SubjectOverride, string Color, GameObject SubjectPossessedBy)
        {
            DidX.Push("XZ", Actor, Verb, Preposition, Object, null, null, Extra, EndMark, SubjectOverride, Color, SubjectPossessedBy);
        }

        static Exception Finalizer(Exception __exception)
        {
            DidX.Pop();
            return __exception;
        }
    }

    [HarmonyPatch(typeof(Messaging), nameof(Messaging.WDidXToYWithZ))]
    static class WDidXToYWithZPatch
    {
        static void Prefix(GameObject Actor, string Verb, string DirectPreposition, GameObject DirectObject,
                           string IndirectPreposition, GameObject IndirectObject, string Extra, string EndMark,
                           string SubjectOverride, string Color, GameObject SubjectPossessedBy)
        {
            DidX.Push("WXZ", Actor, Verb, DirectPreposition, DirectObject, IndirectPreposition, IndirectObject, Extra,
                      EndMark, SubjectOverride, Color, SubjectPossessedBy);
        }

        static Exception Finalizer(Exception __exception)
        {
            DidX.Pop();
            return __exception;
        }
    }

    /// <summary>The one place every DidX message passes: the text is swapped there.</summary>
    [HarmonyPatch]
    static class HandleMessagePatch
    {
        static MethodBase TargetMethod()
        {
            return AccessTools.Method(typeof(Messaging), "HandleMessage", new[]
            {
                typeof(GameObject), typeof(string), typeof(char), typeof(bool), typeof(bool), typeof(GameObject),
                typeof(GameObject), typeof(string), typeof(string),
            });
        }

        static void Prefix(ref string Msg)
        {
            DidX.Render(ref Msg);
        }
    }
}
