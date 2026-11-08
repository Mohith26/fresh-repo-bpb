"""Fetch a deterministic, byte-budgeted sample of files from public repos pinned to a commit."""
import json, random, re, subprocess, sys, urllib.request, hashlib, os

REPOS = {  # name used in Mirendil's Fig. 2 -> (repo, pinned commit). Mapping is inferred from names.
    "codex-sec": ("openai/codex-security", "6e677445f958f0f146e1314fc918fdf143fc8306"),
    "grok-build": ("xai-org/grok-build", "2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8"),
    "openworker": ("andrewyng/openworker", "ddb8b361bd5889703a429af8beaa804554bd858a"),
    "json-render": ("vercel-labs/json-render", "18194121c8f087afacd9a8ef65fbda18374ee039"),
    "scriptc": ("vercel-labs/scriptc", "a57eaacffd59e53b87935c628b2a83aede71b53d"),
    "anydoc": ("firecrawl/anydoc", "e7178e099b6bf9171e2c52b832cbdb4134b69112"),
}
BUDGET = int(os.environ.get("BUDGET_BYTES", 60000))   # bytes of text per repo
MAX_FILE = 12000                                      # truncate long files to this many bytes
CODE_EXT = {".py",".rs",".ts",".tsx",".js",".jsx",".mjs",".cjs",".go",".c",".h",".cc",".cpp",".hpp",".java",".kt",".swift",".rb",".sh",".bash",".zsh",".lua",".zig",".sql",".css",".scss",".html",".vue",".svelte",".cs",".php",".ex",".exs",".ml",".hs",".scala",".dart",".m",".mm",".proto",".graphql"}
DOC_EXT = {".md",".mdx",".rst",".txt",".adoc"}
DATA_EXT = {".json",".jsonc",".yaml",".yml",".toml",".lock",".csv",".tsv",".svg",".xml",".snap",".ini",".cfg",".env",".plist"}
LOCK_NAMES = {"package-lock.json","pnpm-lock.yaml","yarn.lock","Cargo.lock","poetry.lock","uv.lock","bun.lock","Gemfile.lock","go.sum","composer.lock"}
BINARY_EXT = {".png",".jpg",".jpeg",".gif",".ico",".pdf",".woff",".woff2",".ttf",".otf",".zip",".gz",".wasm",".mp4",".mp3",".webp",".bin",".so",".dylib",".a",".jar",".pyc"}

def category(path, text):
    name = path.rsplit("/",1)[-1]
    ext = ("." + name.rsplit(".",1)[-1].lower()) if "." in name else ""
    lines = text.splitlines() or [""]
    avg = sum(len(l) for l in lines) / len(lines)
    if name in LOCK_NAMES or ".min." in name or re.search(r"(^|/)(dist|build|generated|__generated__|vendor|node_modules)/", path) \
       or "@generated" in text[:2000] or "DO NOT EDIT" in text[:2000] or avg > 300:
        return "generated"
    if ext in CODE_EXT or name in {"Makefile","Dockerfile","Justfile"}: return "code"
    if ext in DOC_EXT: return "docs"
    if ext in DATA_EXT: return "config-data"
    return "other"

def tree(repo, sha):
    out = subprocess.run(["gh","api",f"repos/{repo}/git/trees/{sha}?recursive=1"], capture_output=True, text=True, check=True).stdout
    t = json.loads(out)
    assert not t.get("truncated"), f"tree truncated for {repo}"
    return [(x["path"], x["size"]) for x in t["tree"] if x["type"] == "blob"]

def main(outdir="corpus"):
    os.makedirs(outdir, exist_ok=True)
    manifest = []
    for short, (repo, sha) in REPOS.items():
        files = [(p,s) for p,s in tree(repo, sha) if 64 <= s and not any(p.lower().endswith(e) for e in BINARY_EXT)]
        rng = random.Random(int(hashlib.sha256((repo+sha).encode()).hexdigest(), 16))
        rng.shuffle(files)
        used = 0
        for p, s in files:
            if used >= BUDGET: break
            url = f"https://raw.githubusercontent.com/{repo}/{sha}/{p}"
            raw = urllib.request.urlopen(url, timeout=30).read()
            if b"\x00" in raw[:4096]: continue
            try: text = raw.decode("utf-8")
            except UnicodeDecodeError: continue
            text = text.encode("utf-8")[:MAX_FILE].decode("utf-8", "ignore")
            if not text.strip(): continue
            fid = hashlib.sha1(f"{repo}/{p}".encode()).hexdigest()[:12]
            open(f"{outdir}/{fid}.txt","w",encoding="utf-8").write(text)
            manifest.append({"repo_label": short, "repo": repo, "sha": sha, "path": p, "id": fid,
                             "bytes": len(text.encode("utf-8")), "truncated": s > MAX_FILE, "category": category(p, text)})
            used += len(text.encode("utf-8"))
        print(short, repo, "files", sum(1 for m in manifest if m["repo_label"]==short), "bytes", used, file=sys.stderr)
    json.dump(manifest, open(f"{outdir}/manifest.json","w"), indent=1)

if __name__ == "__main__":
    main(*sys.argv[1:])
