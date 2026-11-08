"""Aggregate per-file bits into repo-level bits-per-byte (BPB) and compare protocol effects."""
import json, random, sys
from collections import defaultdict

FIG2 = {  # Mirendil Fig. 2 (bits per byte), copied from mirendil.com/news/pretraining-at-scale-without-a-pretraining-team
    "codex-sec":   {"Kimi-K3": .200, "Mirendil-Base": .228, "Nemotron-550B-Base": .241, "GLM-5.3": .247, "DeepSeek-V4-Pro-Base": .245},
    "grok-build":  {"Kimi-K3": .183, "Mirendil-Base": .210, "Nemotron-550B-Base": .220, "GLM-5.3": .220, "DeepSeek-V4-Pro-Base": .225},
    "openworker":  {"Kimi-K3": .229, "Mirendil-Base": .268, "Nemotron-550B-Base": .296, "GLM-5.3": .287, "DeepSeek-V4-Pro-Base": .304},
    "json-render": {"Kimi-K3": .127, "Mirendil-Base": .127, "Nemotron-550B-Base": .185, "GLM-5.3": .181, "DeepSeek-V4-Pro-Base": .173},
    "native":      {"Kimi-K3": .210, "Mirendil-Base": .257, "Nemotron-550B-Base": .263, "GLM-5.3": .257, "DeepSeek-V4-Pro-Base": .263},
    "scriptc":     {"Kimi-K3": .203, "Mirendil-Base": .219, "Nemotron-550B-Base": .274, "GLM-5.3": .252, "DeepSeek-V4-Pro-Base": .228},
    "anydoc":      {"Kimi-K3": .200, "Mirendil-Base": .246, "Nemotron-550B-Base": .251, "GLM-5.3": .250, "DeepSeek-V4-Pro-Base": .261},
}
FILTERS = {
    "all": lambda r: True,
    "code-only": lambda r: r["category"] == "code",
    "no-generated": lambda r: r["category"] != "generated",
    "code+docs": lambda r: r["category"] in ("code", "docs"),
}

def bpb(rows):
    b = sum(r["bytes"] for r in rows)
    return sum(r["bits"] for r in rows) / b if b else float("nan")

def bootstrap_ci(rows, n=2000, seed=0, stat=bpb):
    """Percentile 95% CI for byte-weighted BPB, resampling files with replacement."""
    if len(rows) < 2: return (float("nan"), float("nan"))
    rng = random.Random(seed); vals = []
    for _ in range(n):
        vals.append(stat([rows[rng.randrange(len(rows))] for _ in rows]))
    vals.sort(); return (vals[int(0.025 * n)], vals[int(0.975 * n) - 1])

def paired_diff_ci(rows_a, rows_b, n=2000, seed=0):
    """95% CI of BPB(a) - BPB(b) over the same files, resampling files jointly."""
    by_id = {r["id"]: r for r in rows_b}
    pairs = [(r, by_id[r["id"]]) for r in rows_a if r["id"] in by_id]
    point = bpb([p[0] for p in pairs]) - bpb([p[1] for p in pairs])
    rng = random.Random(seed); vals = []
    for _ in range(n):
        s = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        vals.append(bpb([p[0] for p in s]) - bpb([p[1] for p in s]))
    vals.sort(); return point, (vals[int(0.025 * n)], vals[int(0.975 * n) - 1])

def load(path):
    rows = [json.loads(l) for l in open(path)]
    seen = {}
    for r in rows: seen[(r["model"], r["protocol"], r["id"])] = r   # last write wins
    return list(seen.values())

def table(rows):
    g = defaultdict(list)
    for r in rows: g[(r["model"].split("/")[-1], r["protocol"], r["repo_label"])].append(r)
    return g

def main(path="results.jsonl"):
    rows = load(path)
    g = table(rows)
    configs = sorted({(m, p) for m, p, _ in g})
    repos = sorted({k[2] for k in g})
    out = {"configs": [], "repos": repos}
    print("## BPB by repo (all sampled files, byte-weighted) with 95% file-bootstrap CI\n")
    print("| model | protocol | " + " | ".join(repos) + " | mean |"); print("|---" * (len(repos) + 3) + "|")
    for m, p in configs:
        cells, vals = [], []
        for repo in repos:
            rs = g.get((m, p, repo), [])
            v = bpb(rs); lo, hi = bootstrap_ci(rs); vals.append(v)
            cells.append(f"{v:.3f} [{lo:.3f}, {hi:.3f}]")
        print(f"| {m} | {p} | " + " | ".join(cells) + f" | {sum(vals)/len(vals):.3f} |")
        out["configs"].append({"model": m, "protocol": p, "bpb": dict(zip(repos, vals))})
    print("\n## File-inclusion filter effect (0.5B, iso-2048): BPB under each filter\n")
    base = [r for r in rows if r["model"].endswith("0.5B") and r["protocol"] == "iso-2048"]
    print("| repo | " + " | ".join(FILTERS) + " | max-min | files (all/code) |"); print("|---" * (len(FILTERS) + 3) + "|")
    for repo in repos:
        rs = [r for r in base if r["repo_label"] == repo]
        v = {k: bpb([r for r in rs if f(r)]) for k, f in FILTERS.items()}
        finite = [x for x in v.values() if x == x]
        print(f"| {repo} | " + " | ".join(f"{x:.3f}" for x in v.values()) + f" | {max(finite)-min(finite):.3f} | {len(rs)}/{sum(r['category']=='code' for r in rs)} |")
    print("\n## Category BPB (0.5B, iso-2048, pooled over repos)\n")
    cats = defaultdict(list)
    for r in base: cats[r["category"]].append(r)
    for c, rs in sorted(cats.items()):
        print(f"- {c}: {bpb(rs):.3f} bits/byte over {len(rs)} files, {sum(r['bytes'] for r in rs)} bytes")
    def diff(a, b, label):
        print(f"\n## Paired difference: {label}\n")
        print("| repo | diff | 95% CI | relative |"); print("|---|---|---|---|")
        for repo in repos:
            ra = [r for r in rows if (r["model"].split('/')[-1], r["protocol"]) == a and r["repo_label"] == repo]
            rb = [r for r in rows if (r["model"].split('/')[-1], r["protocol"]) == b and r["repo_label"] == repo]
            if not ra or not rb: continue
            pt, (lo, hi) = paired_diff_ci(ra, rb)
            print(f"| {repo} | {pt:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {pt/bpb(rb):+.1%} |")
    diff(("Qwen2.5-Coder-1.5B", "iso-2048"), ("Qwen2.5-Coder-0.5B", "iso-2048"), "model size (1.5B minus 0.5B), iso-2048")
    diff(("Qwen2.5-Coder-0.5B", "iso-512"), ("Qwen2.5-Coder-0.5B", "iso-2048"), "context window (512 minus 2048 tokens), 0.5B")
    diff(("Qwen2.5-Coder-0.5B", "xfile-1024"), ("Qwen2.5-Coder-0.5B", "iso-2048"), "cross-file prefix (xfile-1024 minus iso-2048), 0.5B")
    print("\n## Mirendil Fig. 2 per-repo gaps (Mirendil-Base minus next-best non-Kimi model), relative\n")
    for repo, d in FIG2.items():
        mb = d["Mirendil-Base"]; nb = min(v for k, v in d.items() if k not in ("Kimi-K3", "Mirendil-Base"))
        print(f"- {repo}: {mb:.3f} vs {nb:.3f} -> {(mb-nb)/nb:+.1%}")
    json.dump(out, open("results_summary.json", "w"), indent=1)

if __name__ == "__main__":
    main(*sys.argv[1:])
