import math, torch, unittest
from transformers import AutoTokenizer, AutoModelForCausalLM
from score import nll_bits
torch.set_grad_enabled(False)
M = "Qwen/Qwen2.5-Coder-0.5B"
tok = AutoTokenizer.from_pretrained(M); model = AutoModelForCausalLM.from_pretrained(M, torch_dtype=torch.float32).eval()

def exact(ids_ctx, ids_tgt):
    x = torch.tensor([ids_ctx + ids_tgt]); lp = torch.log_softmax(model(x).logits[0], -1)
    n = len(ids_ctx); return -sum(lp[i-1, x[0, i]].item() for i in range(n, x.shape[1])) / math.log(2)

class T(unittest.TestCase):
    text = "def add(a, b):\n    return a + b\n\nclass Stack:\n    def __init__(self):\n        self.items = []\n" * 6
    def test_matches_full_context_when_short(self):
        ids = tok(self.text, add_special_tokens=False)["input_ids"]
        got, n = nll_bits(model, [tok.eos_token_id], ids, 4096, return_count=True)
        self.assertEqual(n, len(ids))
        self.assertAlmostEqual(got, exact([tok.eos_token_id], ids), delta=1e-3 * len(ids))
    def test_each_token_scored_once_with_small_window(self):
        ids = tok(self.text, add_special_tokens=False)["input_ids"]
        for w in (16, 32, 50, 64):
            _, n = nll_bits(model, [tok.eos_token_id], ids, w, return_count=True)
            self.assertEqual(n, len(ids))
    def test_context_prefix_is_not_scored_and_helps(self):
        ids = tok(self.text, add_special_tokens=False)["input_ids"]
        half = len(ids) // 2
        with_ctx, n = nll_bits(model, [tok.eos_token_id] + ids[:half], ids[half:], 4096, return_count=True)
        self.assertEqual(n, len(ids) - half)
        self.assertAlmostEqual(with_ctx, exact([tok.eos_token_id] + ids[:half], ids[half:]), delta=1e-3 * n)
        without, _ = nll_bits(model, [tok.eos_token_id], ids[half:], 4096, return_count=True)
        self.assertLess(with_ctx, without)
    def test_windowing_costs_bits_on_repetitive_text(self):
        ids = tok(self.text, add_special_tokens=False)["input_ids"]
        full = nll_bits(model, [tok.eos_token_id], ids, 4096)
        tiny = nll_bits(model, [tok.eos_token_id], ids, 16)
        self.assertGreater(tiny, full)
if __name__ == "__main__": unittest.main()
