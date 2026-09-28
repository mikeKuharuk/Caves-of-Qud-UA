// Scans Assembly-CSharp.dll metadata without loading it: namespaces, types/members matching
// a pattern, and statistics on the user-string heap (hardcoded string literals).
using System.Reflection.Metadata;
using System.Reflection.Metadata.Ecma335;
using System.Reflection.PortableExecutable;
using System.Text.RegularExpressions;

// Usage: dotnet run asmscan.cs -- [path\to\Assembly-CSharp.dll] <summary|types|members|strings|ldstr|dumpstrings> [regex|outfile]
var gameDir = Environment.GetEnvironmentVariable("QUD_GAME_DIR") ?? @"D:\Steam\steamapps\common\Caves of Qud";
var rest = args.ToList();
var path = rest.Count > 0 && rest[0].EndsWith(".dll", StringComparison.OrdinalIgnoreCase)
    ? rest[0] : Path.Combine(gameDir, "CoQ_Data", "Managed", "Assembly-CSharp.dll");
if (rest.Count > 0 && rest[0].EndsWith(".dll", StringComparison.OrdinalIgnoreCase)) rest.RemoveAt(0);
args = rest.ToArray();
var mode = args.Length > 0 ? args[0] : "summary";
var pattern = args.Length > 1 && mode != "dumpstrings" ? new Regex(args[1], RegexOptions.IgnoreCase) : null;

using var fs = File.OpenRead(path);
using var pe = new PEReader(fs);
var md = pe.GetMetadataReader();

string TypeName(TypeDefinition t)
{
    var ns = md.GetString(t.Namespace);
    var name = md.GetString(t.Name);
    if (t.GetDeclaringType() is { IsNil: false } dt)
        return TypeName(md.GetTypeDefinition(dt)) + "+" + name;
    return string.IsNullOrEmpty(ns) ? name : ns + "." + name;
}

switch (mode)
{
    case "summary":
    {
        var nsCounts = new Dictionary<string, int>();
        foreach (var h in md.TypeDefinitions)
        {
            var t = md.GetTypeDefinition(h);
            var ns = md.GetString(t.Namespace);
            if (t.GetDeclaringType().IsNil)
                nsCounts[ns] = nsCounts.GetValueOrDefault(ns) + 1;
        }
        Console.WriteLine($"Types: {md.TypeDefinitions.Count}, Methods: {md.MethodDefinitions.Count}");
        foreach (var kv in nsCounts.OrderByDescending(k => k.Value).Take(80))
            Console.WriteLine($"{kv.Value,6}  {(kv.Key == "" ? "<global>" : kv.Key)}");
        break;
    }
    case "types":
    {
        foreach (var h in md.TypeDefinitions)
        {
            var n = TypeName(md.GetTypeDefinition(h));
            if (pattern == null || pattern.IsMatch(n)) Console.WriteLine(n);
        }
        break;
    }
    case "members":
    {
        foreach (var h in md.TypeDefinitions)
        {
            var t = md.GetTypeDefinition(h);
            var tn = TypeName(t);
            foreach (var mh in t.GetMethods())
            {
                var mn = md.GetString(md.GetMethodDefinition(mh).Name);
                if (pattern!.IsMatch(tn + "::" + mn)) Console.WriteLine($"M {tn}::{mn}");
            }
            foreach (var fh in t.GetFields())
            {
                var fn = md.GetString(md.GetFieldDefinition(fh).Name);
                if (pattern!.IsMatch(tn + "::" + fn)) Console.WriteLine($"F {tn}::{fn}");
            }
        }
        break;
    }
    case "strings":
    {
        // Walk the #US heap.
        var all = new List<string>();
        var handle = MetadataTokens.UserStringHandle(1);
        while (!handle.IsNil)
        {
            all.Add(md.GetUserString(handle));
            handle = md.GetNextHandle(handle);
        }
        var prose = all.Where(s => Regex.IsMatch(s, @"[A-Za-z]{2,}\s+[A-Za-z]{2,}")).ToList();
        Console.WriteLine($"User strings: {all.Count}, total chars: {all.Sum(s => s.Length)}");
        Console.WriteLine($"Prose-like (two+ words): {prose.Count}, chars: {prose.Sum(s => s.Length)}, words: {prose.Sum(s => Regex.Matches(s, @"[A-Za-z']+").Count)}");
        Console.WriteLine($"Contain '=subject'/'=object'/'=verb' tokens: {all.Count(s => Regex.IsMatch(s, @"=(subject|object|verb|pronouns)"))}");
        Console.WriteLine($"Contain non-ASCII: {all.Count(s => s.Any(c => c > 127))}");
        if (pattern != null)
            foreach (var s in all.Where(s => pattern.IsMatch(s)).Take(200))
                Console.WriteLine("  | " + s.Replace("\n", "\\n"));
        break;
    }
    case "ldstr":
    {
        // Heuristic IL scan: ldstr (0x72) + user-string token (0x70xxxxxx). Groups prose-like
        // literals by namespace and by type, to see where hardcoded player text lives.
        var byNs = new Dictionary<string, (int n, int w)>();
        var byType = new Dictionary<string, (int n, int w)>();
        var usHeapSize = md.GetHeapSize(HeapIndex.UserString);
        foreach (var th in md.TypeDefinitions)
        {
            var t = md.GetTypeDefinition(th);
            var tn = TypeName(t);
            var top = t;
            while (!top.GetDeclaringType().IsNil) top = md.GetTypeDefinition(top.GetDeclaringType());
            var ns = md.GetString(top.Namespace);
            foreach (var mh in t.GetMethods())
            {
                var m = md.GetMethodDefinition(mh);
                if (m.RelativeVirtualAddress == 0) continue;
                var il = pe.GetMethodBody(m.RelativeVirtualAddress).GetILBytes();
                if (il == null) continue;
                for (int i = 0; i + 4 < il.Length; i++)
                {
                    if (il[i] != 0x72 || il[i + 4] != 0x70) continue;
                    int off = il[i + 1] | (il[i + 2] << 8) | (il[i + 3] << 16);
                    if (off <= 0 || off >= usHeapSize) continue;
                    string s;
                    try { s = md.GetUserString(MetadataTokens.UserStringHandle(off)); } catch { continue; }
                    if (!Regex.IsMatch(s, @"[A-Za-z]{2,}\s+[A-Za-z]{2,}")) continue;
                    if (pattern != null && !pattern.IsMatch(tn)) continue;
                    int w = Regex.Matches(s, @"[A-Za-z']+").Count;
                    var a = byNs.GetValueOrDefault(ns); byNs[ns] = (a.n + 1, a.w + w);
                    var b = byType.GetValueOrDefault(tn); byType[tn] = (b.n + 1, b.w + w);
                    i += 4;
                }
            }
        }
        Console.WriteLine($"Prose ldstr sites: {byNs.Values.Sum(v => v.n)}, words: {byNs.Values.Sum(v => v.w)}");
        Console.WriteLine("-- by namespace --");
        foreach (var kv in byNs.OrderByDescending(k => k.Value.w).Take(30))
            Console.WriteLine($"{kv.Value.w,7}w {kv.Value.n,6}x  {(kv.Key == "" ? "<global>" : kv.Key)}");
        Console.WriteLine("-- by type --");
        foreach (var kv in byType.OrderByDescending(k => k.Value.w).Take(60))
            Console.WriteLine($"{kv.Value.w,7}w {kv.Value.n,6}x  {kv.Key}");
        break;
    }
    case "dumpstrings":
    {
        var handle = MetadataTokens.UserStringHandle(1);
        using var w = new StreamWriter(args[1]);
        while (!handle.IsNil)
        {
            w.WriteLine(md.GetUserString(handle).Replace("\r", "\\r").Replace("\n", "\\n"));
            handle = md.GetNextHandle(handle);
        }
        break;
    }
}
