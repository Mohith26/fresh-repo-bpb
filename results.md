## BPB by repo (all sampled files, byte-weighted) with 95% file-bootstrap CI

| model | protocol | anydoc | codex-sec | grok-build | json-render | openworker | scriptc | mean |
|---|---|---|---|---|---|---|---|---|
| Qwen2.5-Coder-0.5B | iso-2048 | 0.534 [0.356, 0.758] | 0.626 [0.477, 0.811] | 0.539 [0.451, 0.658] | 0.523 [0.364, 0.682] | 0.561 [0.466, 0.677] | 0.596 [0.553, 0.637] | 0.563 |
| Qwen2.5-Coder-0.5B | iso-512 | 0.571 [0.386, 0.791] | 0.686 [0.538, 0.859] | 0.595 [0.513, 0.703] | 0.589 [0.413, 0.752] | 0.630 [0.527, 0.745] | 0.644 [0.588, 0.687] | 0.619 |
| Qwen2.5-Coder-0.5B | xfile-1024 | 0.532 [0.354, 0.755] | 0.612 [0.461, 0.803] | 0.541 [0.453, 0.660] | 0.509 [0.347, 0.669] | 0.551 [0.459, 0.666] | 0.597 [0.554, 0.640] | 0.557 |
| Qwen2.5-Coder-1.5B | iso-2048 | 0.474 [0.303, 0.699] | 0.565 [0.424, 0.743] | 0.479 [0.393, 0.595] | 0.476 [0.315, 0.627] | 0.504 [0.413, 0.617] | 0.523 [0.485, 0.564] | 0.504 |

## File-inclusion filter effect (0.5B, iso-2048): BPB under each filter

| repo | all | code-only | no-generated | code+docs | max-min | files (all/code) |
|---|---|---|---|---|---|---|
| anydoc | 0.534 | 0.360 | 0.432 | 0.404 | 0.173 | 20/7 |
| codex-sec | 0.626 | 0.516 | 0.626 | 0.671 | 0.155 | 11/6 |
| grok-build | 0.539 | 0.530 | 0.539 | 0.534 | 0.009 | 9/7 |
| json-render | 0.523 | 0.315 | 0.523 | 0.493 | 0.208 | 12/5 |
| openworker | 0.561 | 0.549 | 0.552 | 0.549 | 0.012 | 13/10 |
| scriptc | 0.596 | 0.586 | 0.607 | 0.590 | 0.021 | 25/14 |

## Category BPB (0.5B, iso-2048, pooled over repos)

- code: 0.500 bits/byte over 49 files, 278398 bytes
- config-data: 0.661 bits/byte over 19 files, 25034 bytes
- docs: 0.753 bits/byte over 11 files, 54017 bytes
- generated: 0.776 bits/byte over 7 files, 26856 bytes
- other: 0.498 bits/byte over 4 files, 14240 bytes

## Paired difference: model size (1.5B minus 0.5B), iso-2048

| repo | diff | 95% CI | relative |
|---|---|---|---|
| anydoc | -0.060 | [-0.086, -0.041] | -11.2% |
| codex-sec | -0.061 | [-0.070, -0.049] | -9.7% |
| grok-build | -0.059 | [-0.067, -0.050] | -11.0% |
| json-render | -0.047 | [-0.061, -0.032] | -8.9% |
| openworker | -0.057 | [-0.065, -0.048] | -10.2% |
| scriptc | -0.073 | [-0.079, -0.062] | -12.2% |

## Paired difference: context window (512 minus 2048 tokens), 0.5B

| repo | diff | 95% CI | relative |
|---|---|---|---|
| anydoc | +0.037 | [+0.019, +0.055] | +7.0% |
| codex-sec | +0.060 | [+0.034, +0.077] | +9.6% |
| grok-build | +0.056 | [+0.042, +0.067] | +10.4% |
| json-render | +0.066 | [+0.037, +0.099] | +12.7% |
| openworker | +0.069 | [+0.041, +0.095] | +12.4% |
| scriptc | +0.048 | [+0.021, +0.066] | +8.1% |

## Paired difference: cross-file prefix (xfile-1024 minus iso-2048), 0.5B

| repo | diff | 95% CI | relative |
|---|---|---|---|
| anydoc | -0.002 | [-0.003, -0.000] | -0.3% |
| codex-sec | -0.014 | [-0.023, -0.003] | -2.3% |
| grok-build | +0.002 | [-0.003, +0.015] | +0.5% |
| json-render | -0.014 | [-0.025, -0.006] | -2.7% |
| openworker | -0.010 | [-0.019, -0.003] | -1.7% |
| scriptc | +0.001 | [-0.007, +0.010] | +0.2% |

## Mirendil Fig. 2 per-repo gaps (Mirendil-Base minus next-best non-Kimi model), relative

- codex-sec: 0.228 vs 0.241 -> -5.4%
- grok-build: 0.210 vs 0.220 -> -4.5%
- openworker: 0.268 vs 0.287 -> -6.6%
- json-render: 0.127 vs 0.173 -> -26.6%
- native: 0.257 vs 0.257 -> +0.0%
- scriptc: 0.219 vs 0.228 -> -3.9%
- anydoc: 0.246 vs 0.250 -> -1.6%
