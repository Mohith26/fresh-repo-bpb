# fresh-repo-bpb

How much do evaluation-protocol choices move "bits per byte on held-out repositories"?

Mirendil's post [Pretraining at scale without a pretraining team](https://mirendil.com/news/pretraining-at-scale-without-a-pretraining-team) (Oct 21, 2026) compares Mirendil-Base with five other models by cross-entropy in bits per byte (BPB) on seven public repositories published after the models were trained (Fig. 2). Bits per byte removes the tokenizer from the comparison, but the number still depends on choices the figure doesn't state: which files count, how much context each token gets, and whether other files from the same repo are in context.

I wanted to know how big those effects are next to the gaps in the figure. I can't run the models in Fig. 2, so I measured the protocol effects with two small open base models (Qwen2.5-Coder 0.5B and 1.5B) on CPU, on public repos matching six of the seven names in Fig. 2. Everything here is free to rerun and pinned to commits.

## Short answer

| effect (Qwen2.5-Coder, 6 repos) | relative change in repo BPB |
|---|---|
| 3x model size (0.5B to 1.5B), same protocol | **-8.9% to -12.2%** |
| context window 2048 to 512 tokens, same model | **+7.0% to +12.7%** |
| which files count (all text vs code only), same model | **-2% to -40%** (json-render: 0.523 vs 0.315) |
| 1,024 tokens of other files from the same repo as prefix | -2.7% to +0.5% |
| Fig. 2: Mirendil-Base vs next-best non-Kimi model | -1.6% to -6.6% (json-render -26.6%, native 0.0%) |

1. **Context length is as big a knob as a 3x larger model.** Cutting the scoring window from 2048 to 512 tokens raised BPB by 7 to 13% on every repo, the same size as going from 0.5B to 1.5B parameters, and larger than most per-repo gaps in Fig. 2. Because the window is counted in tokens, two tokenizers with different bytes-per-token get different amounts of context in bytes, so a fixed token window is not neutral across tokenizers. A byte-denominated context, or the full file, avoids that.
2. **File mix dominates small-sample repo scores.** Pooled over repos, the 0.5B model scores code at 0.50 bits/byte, config/data at 0.66, docs at 0.75 and generated/lock files at 0.78. Dropping non-code files moved json-render from 0.523 to 0.315 and anydoc from 0.534 to 0.360. Whether READMEs, lockfiles and fixtures are in the held-out set changes the number more than the model does.
3. **Compare models paired, file by file.** With 9 to 25 sampled files per repo, an unpaired per-repo BPB has a 95% bootstrap interval 0.08 to 0.40 bits wide. The paired 1.5B minus 0.5B difference on the same files has an interval 0.017 to 0.045 wide and excludes zero on every repo. Small differences such as anydoc's 0.246 vs 0.250 are only meaningful as paired differences on identical bytes.
4. **Cross-file context helped a little.** Prefixing each file with 1,024 tokens from other sampled files of the same repo lowered BPB by up to 2.7% (significant on 4 of 6 repos). That's a small model and random sibling files; a long-context model with the whole repo in context may gain much more, which is one reason to report whether context crosses file boundaries.

Full tables with intervals are in [results.md](results.md).

## What I ran

- **Repos** ([fetch_corpus.py](fetch_corpus.py), pinned commits in the script): `openai/codex-security` (codex-sec), `xai-org/grok-build`, `andrewyng/openworker`, `vercel-labs/json-render`, `vercel-labs/scriptc`, `firecrawl/anydoc`. Matching these to the Fig. 2 names is my inference from the names; I could not identify "native", so it is left out.
- **Sample**: a seeded random sample of text files per repo, about 60 KB per repo (90 files, 399 KB total), files truncated at 12 KB (17 files truncated). Binary files skipped. Each file is tagged code, docs, config-data, generated (lockfiles, minified, dist/, "do not edit" headers, very long lines) or other. File contents are not committed; `corpus/manifest.json` lists repo, commit, path and category, and `fetch_corpus.py` rebuilds the sample exactly.
- **Models**: `Qwen/Qwen2.5-Coder-0.5B` and `Qwen/Qwen2.5-Coder-1.5B` base checkpoints from Hugging Face, float32 on CPU (Apple Silicon arm64, no GPU), transformers 5.22.2, torch 2.15.0. Both were released long before these repos existed.
- **Scoring** ([score.py](score.py)): BPB = summed negative log2-likelihood of a file's tokens / the file's UTF-8 bytes; repo BPB is byte-weighted over files. Protocols: `iso-W` scores each file alone with a window of W tokens (first pass sees the file start, later passes advance by W/2 so every token has at least W/2 tokens of context); `xfile-1024` prepends the last 1,024 tokens of the repo's other sampled files and scores only the file's own tokens.
- **Uncertainty** ([analyze.py](analyze.py)): 2,000-sample file-level bootstrap, percentile 95% intervals, paired resampling for differences.
- **Tests**: `test_score.py` checks the windowed scorer against a single full-context forward pass, that every token is scored exactly once for several window sizes, and that a context prefix is unscored and lowers loss; `test_analyze.py` covers the aggregation and bootstrap helpers.

## What this does not show

- Nothing here measures Mirendil-Base or any model in Fig. 2. The effect sizes are for two small models from one family, and frontier models may be more or less sensitive to each knob.
- The samples are small (60 KB per repo). The filter and category numbers describe these samples, not whole repos.
- I don't know Mirendil's actual protocol. If Fig. 2 already scores whole files with full context and a fixed file filter, finding 1 and 2 are about why that choice matters, not a flaw in the figure.

## Reproduce

```sh
python3.12 -m venv .venv && .venv/bin/pip install torch transformers numpy
.venv/bin/python fetch_corpus.py                      # needs the gh CLI for the tree API
.venv/bin/python test_score.py && .venv/bin/python test_analyze.py
.venv/bin/python score.py Qwen/Qwen2.5-Coder-0.5B iso-2048,iso-512,xfile-1024 results.jsonl
.venv/bin/python score.py Qwen/Qwen2.5-Coder-1.5B iso-2048 results.jsonl
.venv/bin/python analyze.py > results.md
```

Scoring appends one row per file and skips rows already present, so an interrupted run resumes. The full set took about 25 minutes on a shared CPU.
