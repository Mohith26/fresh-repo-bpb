"""Score per-file negative log-likelihood (bits) under a causal LM, for several context protocols.

Protocols
  iso-W     : each file scored on its own with a sliding window of W tokens (stride W/2; every
              token is scored exactly once, with at least W/2 tokens of in-file context after the
              first window).
  xfile-C   : like iso-2048, but the file is preceded by the last C tokens of the other sampled
              files from the same repo (path order). Only the file's own tokens are scored.
Bits per byte = sum(NLL in bits over the file's tokens) / UTF-8 bytes of the file.
The first token of a file is scored given a BOS-like prefix (the tokenizer's eos token for Qwen).
"""
import json, math, sys, time, os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

torch.set_grad_enabled(False)

def load(model_id):
    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    model.eval()
    return tok, model

def nll_bits(model, ctx_ids, tgt_ids, window, return_count=False):
    """Sum of -log2 p(tgt_i | ctx + tgt_<i), evaluated with windows of at most `window` tokens.
    ctx_ids is an unscored prefix (non-empty). The first pass scores up to `window` tokens with
    full context; later passes advance by window//2, so every scored token sees at least
    window//2 tokens of context once the file is longer than the window. Each target token is
    scored exactly once."""
    ids = ctx_ids + tgt_ids
    L, a = len(ids), len(ctx_ids)
    stride = window // 2
    total, count = 0.0, 0
    while a < L:
        b = min(L, max(a + stride, window))
        start = max(0, b - window)
        x = torch.tensor([ids[start:b]])
        logp = torch.log_softmax(model(x).logits[0].float(), dim=-1)
        pos = torch.arange(a - start, b - start)          # positions of scored tokens inside x
        lp = logp[pos - 1, x[0, pos]]
        total += -lp.sum().item() / math.log(2)
        count += len(pos)
        a = b
    return (total, count) if return_count else total

def main(model_id, protocols, outpath, corpus="corpus"):
    tok, model = load(model_id)
    man = json.load(open(f"{corpus}/manifest.json"))
    bos = [tok.eos_token_id]
    texts = {m["id"]: open(f"{corpus}/{m['id']}.txt", encoding="utf-8").read() for m in man}
    toks = {k: tok(v, add_special_tokens=False)["input_ids"] for k, v in texts.items()}
    by_repo = {}
    for m in sorted(man, key=lambda m: m["path"]):
        by_repo.setdefault(m["repo_label"], []).append(m)
    done = set()
    if os.path.exists(outpath):
        for l in open(outpath):
            r = json.loads(l); done.add((r["model"], r["protocol"], r["id"]))
    out = open(outpath, "a")   # one row per file, flushed immediately so interrupted runs resume
    t0 = time.time(); ntok = 0
    for proto in protocols:
        kind, val = proto.split("-"); val = int(val)
        for repo, files in by_repo.items():
            for i, m in enumerate(files):
                if (model_id, proto, m["id"]) in done: continue
                tgt = toks[m["id"]]
                if kind == "iso":
                    bits = nll_bits(model, bos, tgt, val)
                elif kind == "xfile":
                    others = [t for f in files[:i] + files[i+1:] for t in toks[f["id"]]]
                    ctx = bos + others[-val:] if val > 0 else bos
                    bits = nll_bits(model, ctx, tgt, 2048 + val)
                ntok += len(tgt)
                out.write(json.dumps({"model": model_id, "protocol": proto, "id": m["id"], "repo_label": repo,
                             "category": m["category"], "bytes": m["bytes"], "tokens": len(tgt), "bits": bits}) + "\n")
                out.flush()
            print(f"{model_id} {proto} {repo} done {time.time()-t0:.0f}s tok={ntok}", file=sys.stderr, flush=True)
    out.close()

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(","), sys.argv[3])
