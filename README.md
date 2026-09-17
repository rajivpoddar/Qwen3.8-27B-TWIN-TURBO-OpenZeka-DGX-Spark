# Qwen3.8-27B TWIN-TURBO Fable on DGX Spark — OpenZeka profile

An attributed, pinned adaptation of OpenZeka's concurrent Qwen3.8-27B recipe
for the newer **TWIN-TURBO Fable 709-L** fine-tune.

This repository is staging-only. Running the recipe changes the active GPU
service, so prepare and validate it first, then use the normal DGX model
cutover procedure.

## What changed from OpenZeka

OpenZeka's original profile serves `RadixArk/Qwen3.8-27B-NVFP4-BF16-LMHead`
with the external `z-lab/Qwen3.8-27B-DFlash2` drafter and an eight-token draft
window. That drafter was calibrated against base-Qwen logits. It is therefore
not used here: previous testing against the older TURBO-Fable target accepted
only about 1.09 tokens per verification pass and turned speculation into
overhead.

This adaptation keeps OpenZeka's useful DGX Spark serving shape:

- SGLang on one GB10 through `sparkrun`
- FP8 KV cache and BF16 Mamba state
- 8,192-token chunked prefill
- 12 effective running requests and a 64-entry Mamba state pool
- native 262,144-token context
- metrics and cache reporting

It replaces the target with the pinned TWIN-TURBO 709-L NVFP4 checkpoint and
uses its preserved BF16 MTP head through native EAGLE `3/1/4`.

The recipe deliberately leaves Hugging Face and compiler-cache environment
variables to SparkRun 0.3.9. SparkRun owns those persistent mounts; overriding
them in the recipe would cause ignored model-cache settings or throw away
compile caches on container removal.

## Pinned artifacts

| Artifact | Pin |
|---|---|
| Target | `esatapedico/Qwen3.8-27B-TWIN-TURBO-Fable-Cold-Fusion-709-L-Uncensored-NVFP4@7034c5a0c436e4e96fe409812374737030d1687c` |
| Container | `registry.cordata.ai/spark-cluster/sglang-qwen38-27b-dflash2@sha256:2686b3308e8e180060ff22eff2e5c77941a1513bd04c8adf7d6a2898cca18151` |

The checkpoint is W4A16 NVFP4 with the MTP head, linear-attention path,
embeddings and LM head retained in BF16. Its publisher reports a coherent vLLM
smoke test; SGLang compatibility on GB10 remains the first qualification gate.

## Validate without touching the GPU service

```bash
python3 scripts/validate_recipe.py
```

Expected output starts with `RECIPE_VALID`.

## Stage and run

Install and configure `sparkrun`, then stage the immutable target and container
without replacing a live service according to your local sparkrun workflow.
SparkRun consumes the top-level `model_revision` pin during download, cache
validation, VRAM detection and synchronization; the same pin is passed to
SGLang at launch.

The recipe requires `SGLANG_API_KEY` in the resolved SparkRun environment. Put
the secret in a mode-`0600` cluster `env_file` and map it into the saved
cluster's `env`; do not add the key to this recipe or pass it on the command
line. The server refuses unauthenticated API requests and the key therefore
also needs to match the clients and dashboard bound to port `30000`.

During the approved cutover window:

```bash
sparkrun run ./openzeka-twin-turbo.yaml --rootful --no-follow --no-rm
```

The recipe listens on port `30000` and exposes the model alias
`qwen3.8-27b`.

## Spark Dashboard integration

Spark Dashboard is endpoint-bound, not model-bound. The installed dashboard on
the Spark remains bound to the stable SGLang endpoint on port `30000`, so a
model swap does not require a dashboard restart or state migration.

This recipe now makes that contract executable: after SparkRun's engine health
gate, its `post_commands` require an SGLang-formatted `/metrics` response from
the model endpoint and an `ok` response from Spark Dashboard `/healthz` on port
`3000`. A launch fails visibly if either side is unavailable.

To audit the full live binding on the DGX without printing its API key, run:

```bash
./scripts/check-dashboard.sh
```

The expected terminal receipt is:

```text
dashboard=ready engine=sglang endpoint=http://192.168.68.113:30000 metrics=sglang
```

## Required qualification before slot use

1. Confirm the checkpoint loads under the pinned SGLang image with no missing
   `compressed-tensors` or MTP tensors.
2. Require authenticated model discovery and both OpenAI and Anthropic request
   proofs through the production gateway.
3. Verify `qwen3_coder` tool calls and the model's patched chat template.
4. Run one four-concurrent-request benchmark and capture TTFT, aggregate decode,
   queue depth, KV capacity and MTP acceptance.
5. Roll back if native-MTP acceptance, tool structure or output stability is
   worse than the current service.

## Sources and attribution

- [OpenZeka: Qwen3.8-27B on DGX Spark — 48 tok/s](https://blog.openzeka.com/en/qwen3-8-27b-on-dgx-spark-48-tok-s/)
- [TWIN-TURBO Fable 709-L source](https://huggingface.co/DavidAU/Qwen3.8-27B-TWIN-TURBO-Fable-Cold-Fusion-709-L-Uncensored)
- [NVFP4 derivative used here](https://huggingface.co/esatapedico/Qwen3.8-27B-TWIN-TURBO-Fable-Cold-Fusion-709-L-Uncensored-NVFP4)

OpenZeka's article does not provide a Git repository to fork, so this repository
preserves the source URL and serving shape while recording every changed model
and speculative-decoding decision explicitly.
