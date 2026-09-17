#!/usr/bin/env python3
"""Fail-closed static validation for the staged sparkrun recipe."""

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / "openzeka-twin-turbo.yaml"
EXPECTED_MODEL = (
    "esatapedico/Qwen3.8-27B-TWIN-TURBO-Fable-Cold-Fusion-709-L-"
    "Uncensored-NVFP4"
)
EXPECTED_REVISION = "7034c5a0c436e4e96fe409812374737030d1687c"
EXPECTED_IMAGE_DIGEST = (
    "sha256:2686b3308e8e180060ff22eff2e5c77941a1513bd04c8adf7d6a2898cca18151"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"recipe validation failed: {message}")


def main() -> None:
    data = yaml.safe_load(RECIPE.read_text())
    defaults = data.get("defaults", {})
    command = data.get("command", "")

    require(data.get("recipe_version") == "2", "unexpected recipe version")
    require(data.get("runtime") == "sglang", "runtime must be sglang")
    require(data.get("model") == EXPECTED_MODEL, "target checkpoint drift")
    require(data.get("model_revision") == EXPECTED_REVISION, "target revision drift")
    require(
        str(data.get("container", "")).endswith("@" + EXPECTED_IMAGE_DIGEST),
        "container image is not digest-pinned",
    )

    require("--speculative-algorithm EAGLE" in command, "native MTP/EAGLE is missing")
    require("--speculative-draft-model-path" not in command, "external drafter is forbidden")
    require("DFLASH" not in command, "DFlash must not be enabled for this fine-tune")
    require(defaults.get("kv_cache_dtype") == "fp8_e4m3", "FP8 KV declaration is missing")
    require("--kv-cache-dtype {kv_cache_dtype}" in command, "FP8 KV cache is missing")
    require("--mamba-ssm-dtype bfloat16" in command, "Mamba state must remain BF16")
    require(defaults.get("max_running_requests") == 12, "OpenZeka admission shape drift")
    require(defaults.get("chunked_prefill_size") == 8192, "OpenZeka prefill shape drift")
    require(defaults.get("context_length") == 262144, "context must remain native 262K")
    require(defaults.get("speculative_num_draft_tokens") == 4, "native MTP draft drift")

    print(
        "RECIPE_VALID "
        f"model={data['model']} revision={data['model_revision']} "
        f"engine=EAGLE max_running={defaults['max_running_requests']} "
        f"chunk={defaults['chunked_prefill_size']} context={defaults['context_length']}"
    )


if __name__ == "__main__":
    try:
        main()
    except yaml.YAMLError as exc:
        print(f"recipe validation failed: invalid YAML: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
