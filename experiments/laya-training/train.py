"""Standalone training and calibration script for Laya on daily predictor data.

Fine-tunes ModernBERT-large using LoRA adapters on historical pre-market contexts,
followed by post-hoc temperature calibration to minimize Brier score.
Completely isolated from apps/engine runtime.
"""

import argparse
import json
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset


class LayaDataset(Dataset):
    """PyTorch Dataset for Laya typed-decision direction predictions."""

    def __init__(self, jsonl_path: str, tokenizer, max_seq_length: int = 8192):
        self.samples = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.samples.append(json.loads(line))

        self.tokenizer = tokenizer
        self.max_seq_length = max_seq_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        item = self.samples[idx]
        state = item["state"]
        q = item["questions"]["direction"]
        instructions = q["instructions"]
        opts = q["options"]

        prompt = (
            f"Instruction: {instructions}\n"
            f"Options:\n"
            f"UP: {opts.get('UP', '')}\n"
            f"DOWN: {opts.get('DOWN', '')}\n\n"
            f"Market Context:\n{state}"
        )

        gold_choice = item["gold"]["direction"]["choice"].upper()
        label = 1 if gold_choice == "UP" else 0

        encoding = self.tokenizer(
            prompt,
            max_length=self.max_seq_length,
            truncation=True,
            padding=False,
            return_tensors=None,
        )

        return {
            "input_ids": encoding["input_ids"],
            "attention_mask": encoding.get("attention_mask", [1] * len(encoding["input_ids"])),
            "label": label,
            "target_date": item.get("metadata", {}).get("target_date", ""),
        }


def collate_fn(batch, pad_token_id=0):
    """Dynamic padding to max sequence length in current batch."""
    max_len = max(len(b["input_ids"]) for b in batch)
    input_ids = []
    attention_mask = []
    labels = []
    dates = []

    for b in batch:
        ids = b["input_ids"]
        mask = b["attention_mask"]
        pad_len = max_len - len(ids)

        input_ids.append(ids + [pad_token_id] * pad_len)
        attention_mask.append(mask + [0] * pad_len)
        labels.append(b["label"])
        dates.append(b["target_date"])

    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "attention_mask": torch.tensor(attention_mask, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
        "dates": dates,
    }


class TemperatureScaler(nn.Module):
    """Post-hoc temperature scaling for calibrated decision probabilities."""

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits):
        return logits / torch.clamp(self.temperature, min=0.1, max=5.0)

    def fit(self, logits: torch.Tensor, labels: torch.Tensor, lr: float = 0.01, max_iter: int = 100):
        optimizer = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)
        criterion = nn.CrossEntropyLoss()

        def eval_loss():
            optimizer.zero_grad()
            scaled_logits = self.forward(logits)
            loss = criterion(scaled_logits, labels)
            loss.backward()
            return loss

        optimizer.step(eval_loss)
        return float(torch.clamp(self.temperature, min=0.1, max=5.0).item())


def calculate_brier_score(probs: list[float], labels: list[int]) -> float:
    """Calculate mean Brier score: (p - y)^2."""
    if not probs:
        return 0.0
    scores = [(p - y) ** 2 for p, y in zip(probs, labels, strict=False)]
    return sum(scores) / len(scores)


def train_laya(
    model_name: str = "convaiinnovations/laya-typed-decisions",
    data_dir: str = "data",
    output_dir: str = "output",
    epochs: int = 3,
    batch_size: int = 1,
    grad_accum_steps: int = 8,
    learning_rate: float = 2e-5,
    max_seq_length: int = 8192,
    lora_r: int = 16,
    lora_alpha: int = 16,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    fp16: bool = torch.cuda.is_available(),
):
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    base_path = Path(__file__).resolve().parent
    train_path = base_path / data_dir / "train.jsonl"
    val_path = base_path / data_dir / "val.jsonl"
    out_dir = base_path / output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not train_path.exists() or not val_path.exists():
        raise FileNotFoundError(f"Missing {train_path} or {val_path}. Run export_dataset.py first.")

    print(f"Loading tokenizer and model: {model_name}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    except Exception as e:
        print(f"Could not load tokenizer from {model_name}, falling back to answerdotai/ModernBERT-large: {e}")
        tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token or "[PAD]"

    print("Building datasets...")
    train_ds = LayaDataset(str(train_path), tokenizer, max_seq_length=max_seq_length)
    val_ds = LayaDataset(str(val_path), tokenizer, max_seq_length=max_seq_length)

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.pad_token_id),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=lambda b: collate_fn(b, pad_token_id=tokenizer.pad_token_id),
    )

    print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}")

    print("Loading base classification model...")
    model_dtype = (
        torch.bfloat16
        if (torch.cuda.is_available() and torch.cuda.is_bf16_supported())
        else torch.float32
    )
    try:
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=2,
            id2label={0: "DOWN", 1: "UP"},
            label2id={"DOWN": 0, "UP": 1},
            dtype=model_dtype,
        )
    except Exception as e:
        print(f"Could not load {model_name}, loading base ModernBERT-large: {e}")
        model = AutoModelForSequenceClassification.from_pretrained(
            "answerdotai/ModernBERT-large",
            num_labels=2,
            id2label={0: "DOWN", 1: "UP"},
            label2id={"DOWN": 0, "UP": 1},
            dtype=model_dtype,
        )

    # Enable gradient checkpointing to allow larger batch sizes
    model.gradient_checkpointing_enable()

    # Configure LoRA adapters across attention and MLP projections
    peft_config = LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=["Wqkv", "Wo", "Wi"],
        bias="none",
    )
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()
    model.to(device)

    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()

    print(f"\nStarting fine-tuning ({epochs} epochs, lr={learning_rate}, effective batch size={batch_size * grad_accum_steps})...")

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        optimizer.zero_grad()

        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            loss = criterion(logits, labels) / grad_accum_steps
            loss.backward()

            total_loss += loss.item() * grad_accum_steps

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad()

        avg_loss = total_loss / len(train_loader)
        print(f"Epoch {epoch}/{epochs} | Train Loss: {avg_loss:.4f}")

    # Validation evaluation & logit collection for temperature calibration
    print("\nRunning validation evaluation and temperature calibration...")
    model.eval()
    val_logits_list = []
    val_labels_list = []

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            val_logits_list.append(outputs.logits.cpu())
            val_labels_list.append(labels.cpu())

    val_logits = torch.cat(val_logits_list, dim=0).float()
    val_labels = torch.cat(val_labels_list, dim=0)

    # Raw metrics
    raw_probs = torch.softmax(val_logits, dim=-1)[:, 1].numpy().tolist()
    raw_preds = (torch.softmax(val_logits, dim=-1)[:, 1] >= 0.5).long().numpy().tolist()
    labels_np = val_labels.numpy().tolist()

    raw_accuracy = sum(p == y for p, y in zip(raw_preds, labels_np, strict=False)) / len(labels_np)
    raw_brier = calculate_brier_score(raw_probs, labels_np)

    # Fit temperature scaler
    scaler = TemperatureScaler()
    fitted_temp = scaler.fit(val_logits, val_labels)

    scaled_logits = scaler(val_logits)
    cal_probs = torch.softmax(scaled_logits, dim=-1)[:, 1].detach().numpy().tolist()
    cal_brier = calculate_brier_score(cal_probs, labels_np)

    # Fit Platt scaler (slope w and intercept b)
    platt_w = 1.0
    platt_b = 0.0
    platt_brier = cal_brier
    platt_acc = raw_accuracy
    try:
        from sklearn.linear_model import LogisticRegression

        delta_z = (val_logits[:, 1] - val_logits[:, 0]).numpy().reshape(-1, 1)
        y_np = val_labels.numpy()
        lr_cal = LogisticRegression(C=1.0, solver="lbfgs")
        lr_cal.fit(delta_z, y_np)
        platt_w = float(lr_cal.coef_[0][0])
        platt_b = float(lr_cal.intercept_[0])
        platt_probs = lr_cal.predict_proba(delta_z)[:, 1].tolist()
        platt_brier = calculate_brier_score(platt_probs, labels_np)
        platt_acc = sum((p >= 0.5) == y for p, y in zip(platt_probs, labels_np, strict=False)) / len(labels_np)
    except Exception as e:
        print(f"Platt scaling skipped: {e}")

    print("\n" + "=" * 55)
    print("VALIDATION BENCHMARK RESULTS")
    print("=" * 55)
    print(f"Directional Accuracy:       {raw_accuracy * 100.0:.1f}%")
    print(f"Uncalibrated Brier Score:   {raw_brier:.4f}")
    print(f"Fitted Calibration Temp:    {fitted_temp:.3f}")
    print(f"Temperature Brier Score:    {cal_brier:.4f} (improvement: {raw_brier - cal_brier:+.4f})")
    print(f"Platt Scaled Accuracy:      {platt_acc * 100.0:.1f}%")
    print(f"Platt Calibrated Brier:     {platt_brier:.4f} (w={platt_w:.4f}, b={platt_b:.4f})")
    print("=" * 55)

    # Save artifacts
    print(f"\nSaving LoRA adapters and calibration config to {out_dir}...")
    model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    cal_config = {
        "base_model": model_name,
        "method": "platt_scaling",
        "platt_w": platt_w,
        "platt_b": platt_b,
        "fitted_temperature": fitted_temp,
        "raw_accuracy": raw_accuracy,
        "platt_accuracy": platt_acc,
        "uncalibrated_brier": raw_brier,
        "temperature_brier": cal_brier,
        "calibrated_brier": platt_brier,
        "max_seq_length": max_seq_length,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
    }
    with open(out_dir / "laya_calibration_config.json", "w") as f:
        json.dump(cal_config, f, indent=2)

    print("Training and calibration artifacts successfully saved.")
    return cal_config


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Laya on daily predictor data with LoRA.")
    parser.add_argument("--model-name", default="convaiinnovations/laya-typed-decisions", help="Hugging Face model checkpoint.")
    parser.add_argument("--data-dir", default="data", help="Directory with train.jsonl and val.jsonl.")
    parser.add_argument("--output-dir", default="output", help="Output directory for fine-tuned weights.")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs.")
    parser.add_argument("--batch-size", type=int, default=4, help="Per-device batch size.")
    parser.add_argument("--grad-accum-steps", type=int, default=2, help="Gradient accumulation steps.")
    parser.add_argument("--learning-rate", type=float, default=3e-5, help="Learning rate.")
    parser.add_argument("--max-seq-length", type=int, default=8192, help="Max sequence length for ModernBERT.")
    parser.add_argument("--lora-r", type=int, default=16, help="LoRA rank.")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha.")
    args = parser.parse_args()

    train_laya(
        model_name=args.model_name,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum_steps=args.grad_accum_steps,
        learning_rate=args.learning_rate,
        max_seq_length=args.max_seq_length,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
    )


if __name__ == "__main__":
    main()
