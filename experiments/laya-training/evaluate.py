"""Standalone evaluation script comparing fine-tuned Laya against zero-shot and historical models.

Evaluates on data/val.jsonl and pulls historical predictions from Supabase
for the exact same validation dates to produce a side-by-side performance table.
Completely isolated from apps/engine runtime.
"""

import argparse
import json
import math
from pathlib import Path


def calculate_brier_score(prob_up: float, actual_direction: str) -> float:
    """Calculate Brier score: (p - y)^2 for binary direction."""
    y = 1.0 if actual_direction.upper() == "UP" else 0.0
    return float((prob_up - y) ** 2)


def compute_calibrated_probability(
    logit_down: float,
    logit_up: float,
    calibration_cfg: dict | None = None,
) -> float:
    """Compute calibrated probability for UP given raw logits and calibration config.

    Supports Platt scaling (method='platt_scaling' with platt_w and platt_b)
    as well as scalar temperature scaling (fitted_temperature).
    """
    delta = logit_up - logit_down
    if not calibration_cfg:
        delta_clamped = max(min(delta, 50.0), -50.0)
        return 1.0 / (1.0 + math.exp(-delta_clamped))

    method = calibration_cfg.get("method")
    if method == "platt_scaling" or "platt_w" in calibration_cfg:
        w = float(calibration_cfg.get("platt_w", 1.0))
        b = float(calibration_cfg.get("platt_b", 0.0))
        scaled = w * delta + b
        scaled_clamped = max(min(scaled, 50.0), -50.0)
        return 1.0 / (1.0 + math.exp(-scaled_clamped))

    temp = float(calibration_cfg.get("fitted_temperature", 1.0))
    temp = max(temp, 0.01)
    scaled_delta = delta / temp
    scaled_delta_clamped = max(min(scaled_delta, 50.0), -50.0)
    return 1.0 / (1.0 + math.exp(-scaled_delta_clamped))


def evaluate_laya(
    model_dir: str = "output",
    val_file: str = "data/val.jsonl",
    base_model: str = "convaiinnovations/laya-typed-decisions",
    device: str | None = None,
):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    base_path = Path(__file__).resolve().parent
    val_path = base_path / val_file
    ckpt_path = base_path / model_dir
    config_file = ckpt_path / "laya_calibration_config.json"

    if not val_path.exists():
        raise FileNotFoundError(f"Missing {val_path}. Run export_dataset.py first.")

    val_samples = []
    with open(val_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                val_samples.append(json.loads(line.strip()))

    cal_cfg = None
    if config_file.exists():
        with open(config_file, "r") as f:
            cal_cfg = json.load(f)
            base_model = cal_cfg.get("base_model", base_model)

    print(f"Loading base model {base_model} and adapters from {ckpt_path}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(ckpt_path)
    except Exception:
        tokenizer = AutoTokenizer.from_pretrained(base_model)

    raw_base = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=2,
        id2label={0: "DOWN", 1: "UP"},
        label2id={"DOWN": 0, "UP": 1},
        torch_dtype=torch.float32,
    )

    if (ckpt_path / "adapter_config.json").exists():
        model = PeftModel.from_pretrained(raw_base, ckpt_path)
        print("Successfully loaded LoRA adapters.")
    else:
        model = raw_base
        print("No LoRA adapters found, evaluating base model zero-shot.")

    model.to(device)
    model.eval()

    laya_results = []

    print(f"Running inference across {len(val_samples)} validation sessions...")
    with torch.no_grad():
        for item in val_samples:
            target_date = item["metadata"]["target_date"]
            actual_dir = item["gold"]["direction"]["choice"].upper()

            q = item["questions"]["direction"]
            prompt = (
                f"Instruction: {q['instructions']}\n"
                f"Options:\n"
                f"UP: {q['options'].get('UP', '')}\n"
                f"DOWN: {q['options'].get('DOWN', '')}\n\n"
                f"Market Context:\n{item['state']}"
            )

            enc = tokenizer(prompt, max_length=8192, truncation=True, return_tensors="pt").to(device)
            logits = model(**enc).logits
            prob_up = compute_calibrated_probability(
                logit_down=float(logits[0, 0].item()),
                logit_up=float(logits[0, 1].item()),
                calibration_cfg=cal_cfg,
            )

            pred_dir = "UP" if prob_up >= 0.5 else "DOWN"
            conf = prob_up if pred_dir == "UP" else (1.0 - prob_up)
            is_correct = pred_dir == actual_dir
            brier = calculate_brier_score(prob_up, actual_dir)

            laya_results.append(
                {
                    "target_date": target_date,
                    "actual": actual_dir,
                    "predicted": pred_dir,
                    "prob_up": prob_up,
                    "confidence": conf,
                    "is_correct": is_correct,
                    "brier": brier,
                }
            )

    # Compute aggregate metrics
    laya_acc = sum(r["is_correct"] for r in laya_results) / len(laya_results)
    laya_brier = sum(r["brier"] for r in laya_results) / len(laya_results)

    # Try fetching historical arena model benchmarks for the exact same validation dates
    arena_benchmarks = fetch_historical_arena_benchmarks(
        val_dates=[r["target_date"] for r in laya_results]
    )

    # Print comparative results
    print("\n" + "=" * 70)
    print("OUT-OF-SAMPLE VALIDATION BENCHMARK (Exact Same Dates)")
    print("=" * 70)
    print(f"{'Model / System':<30} | {'Accuracy':<10} | {'Brier Score':<12} | {'Sessions'}")
    print("-" * 70)
    print(f"{'Fine-Tuned Laya (LoRA+Temp)':<30} | {laya_acc * 100.0:>8.1f}% | {laya_brier:>12.4f} | {len(laya_results):>8}")

    for name, m in arena_benchmarks.items():
        acc_str = f"{m['accuracy'] * 100.0:>8.1f}%" if m["total"] > 0 else "N/A"
        brier_str = f"{m['brier']:>12.4f}" if m["total"] > 0 else "N/A"
        print(f"{name:<30} | {acc_str} | {brier_str} | {m['total']:>8}")

    print("=" * 70)
    print("Note: Lower Brier score is better (0.00 = perfect calibration, 0.25 = random 50/50 guessing).")


def fetch_historical_arena_benchmarks(val_dates: list[str]) -> dict[str, dict]:
    """Query Supabase read-only for historical models' actual predictions on validation dates."""
    try:
        from export_dataset import get_supabase_client

        client = get_supabase_client()
        resp = (
            client.table("daily_predictions")
            .select("model_name, target_date, predicted_direction, actual_direction, confidence, brier_score, is_correct")
            .in_("target_date", val_dates)
            .eq("status", "evaluated")
            .execute()
        )
        rows = resp.data or []

        models: dict[str, dict] = {}
        for r in rows:
            m_name = r.get("model_name", "unknown")
            if m_name not in models:
                models[m_name] = {"correct": 0, "total": 0, "brier_sum": 0.0}

            models[m_name]["total"] += 1
            if r.get("is_correct"):
                models[m_name]["correct"] += 1

            # Compute or extract brier
            b = r.get("brier_score")
            if b is not None:
                models[m_name]["brier_sum"] += float(b)
            else:
                conf = float(r.get("confidence", 50.0)) / 100.0
                actual = str(r.get("actual_direction", "")).upper()
                pred = str(r.get("predicted_direction", "")).upper()
                prob = conf if pred == "UP" else (1.0 - conf)
                models[m_name]["brier_sum"] += calculate_brier_score(prob, actual)

        summary = {}
        for m_name, stats in models.items():
            tot = stats["total"]
            summary[m_name] = {
                "accuracy": stats["correct"] / tot if tot > 0 else 0.0,
                "brier": stats["brier_sum"] / tot if tot > 0 else 0.25,
                "total": tot,
            }
        return summary
    except Exception as e:
        print(f"Note: Could not query historical benchmark comparison ({e}).")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned Laya model against validation set.")
    parser.add_argument("--model-dir", default="output", help="Directory with LoRA weights and calibration config.")
    parser.add_argument("--val-file", default="data/val.jsonl", help="Validation JSONL file.")
    parser.add_argument("--base-model", default="convaiinnovations/laya-typed-decisions", help="Base model identifier.")
    args = parser.parse_args()

    evaluate_laya(model_dir=args.model_dir, val_file=args.val_file, base_model=args.base_model)


if __name__ == "__main__":
    main()
