"""Test and benchmark inference against fine-tuned and base models.

Works directly with Ollama's OpenAI-compatible API endpoint (http://localhost:11434/v1)
or vLLM (http://localhost:8000/v1). Extracts genuine model confidence from token logprobs.
"""

import argparse
import json
import math
from pathlib import Path
from openai import OpenAI


def extract_confidence_from_logprobs(choice_logprobs, predicted_direction: str) -> float | None:
    """Extract mathematical confidence from the direction token logprobs."""
    if not choice_logprobs or not hasattr(choice_logprobs, "content") or not choice_logprobs.content:
        return None

    target_dir = predicted_direction.upper()
    opp_dir = "DOWN" if target_dir == "UP" else "UP"

    for token_info in choice_logprobs.content:
        token_str = token_info.token.strip().strip('"').upper()
        if token_str == target_dir:
            lp_target = token_info.logprob
            prob_target = math.exp(lp_target)

            prob_opp = 0.0
            if hasattr(token_info, "top_logprobs") and token_info.top_logprobs:
                for top in token_info.top_logprobs:
                    top_str = top.token.strip().strip('"').upper()
                    if top_str == opp_dir:
                        prob_opp = math.exp(top.logprob)
                        break

            if prob_opp > 0:
                normalized_prob = prob_target / (prob_target + prob_opp)
                return round(normalized_prob * 100.0, 1)

            return round(min(max(prob_target, 0.5), 0.99) * 100.0, 1)

    return None


def query_model(client: OpenAI, model_name: str, messages: list[dict]):
    """Query model with logprob capture and fallback."""
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.1,
            max_tokens=256,
            logprobs=True,
            top_logprobs=5,
        )
    except Exception:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.1,
            max_tokens=256,
        )
    return response.choices[0]


def run_benchmark(
    endpoint: str = "http://localhost:11434/v1",
    model_name: str = "qwen3.8-predictor",
):
    """Run full benchmark evaluation across all validation sessions."""
    val_file = Path(__file__).resolve().parent / "data" / "val.jsonl"
    if not val_file.exists():
        raise FileNotFoundError(f"Validation dataset not found at {val_file}")

    with open(val_file, encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]

    client = OpenAI(base_url=endpoint, api_key="ollama")

    print("\n=======================================================")
    print(f"BENCHMARKING: {model_name} on {len(samples)} out-of-sample forward sessions")
    print(f"Endpoint: {endpoint}")
    print("=======================================================\n")

    correct = 0
    total = 0
    brier_scores = []
    return_errors = []
    valid_json_count = 0

    for idx, sample in enumerate(samples, 1):
        target_date = sample["metadata"]["target_date"]
        actual_dir = sample["metadata"]["actual_direction"]
        actual_ret = sample["metadata"]["actual_return_pct"]

        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in sample["messages"]
            if m["role"] in ("system", "user")
        ]

        choice = query_model(client, model_name, messages)
        raw_output = choice.message.content or ""

        try:
            parsed = json.loads(raw_output)
            valid_json_count += 1
            pred_dir = str(parsed.get("predicted_direction", "")).upper()
            pred_ret = parsed.get("expected_return_pct")

            is_hit = pred_dir == actual_dir
            if is_hit:
                correct += 1
            total += 1

            conf = extract_confidence_from_logprobs(getattr(choice, "logprobs", None), pred_dir)
            if conf is None:
                conf = 50.0  # Default uninformative prior

            brier = round((conf / 100.0 - (1.0 if is_hit else 0.0)) ** 2, 4)
            brier_scores.append(brier)

            if pred_ret is not None:
                return_errors.append(abs(float(pred_ret) - float(actual_ret)))

            status = "HIT " if is_hit else "MISS"
            print(
                f"[{idx:02d}/{len(samples):02d}] {target_date} | "
                f"Actual: {actual_dir:4s} ({actual_ret:+5.2f}%) | "
                f"Pred: {pred_dir:4s} ({pred_ret:+5.2f}%) | "
                f"Conf: {conf:4.1f}% | Brier: {brier:.4f} -> {status}"
            )
        except json.JSONDecodeError:
            total += 1
            print(f"[{idx:02d}/{len(samples):02d}] {target_date} | Output was not valid JSON: {raw_output[:60]}...")

    accuracy = (correct / total * 100.0) if total > 0 else 0.0
    avg_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.2500
    avg_ret_err = (sum(return_errors) / len(return_errors)) if return_errors else 0.0
    json_rate = (valid_json_count / len(samples) * 100.0) if samples else 0.0

    print("\n----------------- BENCHMARK SCORECARD -----------------")
    print(f"Evaluated Model:            {model_name}")
    print(f"Total Forward Sessions:     {len(samples)}")
    print(f"JSON Format Compliance:     {json_rate:.1f}% ({valid_json_count}/{len(samples)})")
    print(f"Directional Accuracy:       {accuracy:.1f}% ({correct}/{total})")
    print(f"Average Brier Score:        {avg_brier:.4f} (lower is better, baseline: 0.2500)")
    print(f"Mean Absolute Return Error: {avg_ret_err:.2f}%")
    print("-------------------------------------------------------\n")


def run_single_prediction(
    endpoint: str = "http://localhost:11434/v1",
    model_name: str = "qwen3.8-predictor",
    sample_index: int = -1,
):
    """Load a single validation sample and test inference."""
    val_file = Path(__file__).resolve().parent / "data" / "val.jsonl"
    if not val_file.exists():
        raise FileNotFoundError(f"Validation dataset not found at {val_file}")

    with open(val_file, encoding="utf-8") as f:
        samples = [json.loads(line) for line in f]

    sample = samples[sample_index]
    target_date = sample["metadata"]["target_date"]
    actual_dir = sample["metadata"]["actual_direction"]
    actual_ret = sample["metadata"]["actual_return_pct"]

    print(f"Testing validation date: {target_date}")
    print(f"Ground truth market outcome: {actual_dir} ({actual_ret:+.2f}%)")

    client = OpenAI(base_url=endpoint, api_key="ollama")

    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in sample["messages"]
        if m["role"] in ("system", "user")
    ]

    print("Querying model endpoint...")
    choice = query_model(client, model_name, messages)
    raw_output = choice.message.content or ""
    print("\n=== RAW MODEL OUTPUT ===")
    print(raw_output)

    try:
        parsed = json.loads(raw_output)
        pred_dir = str(parsed.get("predicted_direction", "")).upper()
        pred_ret = parsed.get("expected_return_pct")
        is_hit = pred_dir == actual_dir
        conf = extract_confidence_from_logprobs(getattr(choice, "logprobs", None), pred_dir)

        print("\n=== PARSED PREDICTION EVALUATION ===")
        print(f"Predicted Direction: {pred_dir} | Actual: {actual_dir} -> {'CORRECT' if is_hit else 'INCORRECT'}")
        print(f"Predicted Return:    {pred_ret}% | Actual: {actual_ret:+.2f}%")
        if conf is not None:
            print(f"Model Confidence:    {conf}% (derived from token logprobs)")
            brier = round((conf / 100.0 - (1.0 if is_hit else 0.0)) ** 2, 4)
            print(f"Session Brier Score: {brier}")
        else:
            print("Model Confidence:    Not provided by endpoint (logprobs disabled)")
    except json.JSONDecodeError:
        print("\nWarning: Output could not be parsed as valid JSON.")


def main():
    parser = argparse.ArgumentParser(description="Test and benchmark predictor inference.")
    parser.add_argument("--endpoint", default="http://localhost:11434/v1", help="Base URL of inference API")
    parser.add_argument("--model", default="qwen3.8-predictor", help="Model name registered in server")
    parser.add_argument(
        "--sample-index", type=int, default=-1, help="Index of validation sample to evaluate (-1 for latest)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run full benchmark across all 20 out-of-sample forward sessions"
    )
    args = parser.parse_args()

    if args.all:
        run_benchmark(endpoint=args.endpoint, model_name=args.model)
    else:
        run_single_prediction(endpoint=args.endpoint, model_name=args.model, sample_index=args.sample_index)


if __name__ == "__main__":
    main()
