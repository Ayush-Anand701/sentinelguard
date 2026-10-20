"""
SentinelGuard Benchmark Evaluation Script.

Runs SentinelGuard against the benchmark dataset and computes:
- Precision, Recall, F1 score
- False positive rate
- Average latency per conversation
- Comparison against a keyword-blocklist baseline

Run from the repo root:
    python benchmarks/evaluate.py
"""

import json
import time
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from sentinelguard import SentinelGuard


# ---------------------------------------------------------------------------
# Keyword blocklist baseline
# Represents the simplest possible defense — what SentinelGuard improves on
# ---------------------------------------------------------------------------

BLOCKLIST_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "you are now dan",
    "do anything now",
    "no restrictions",
    "developer mode",
    "synthesise",
    "synthesize",
    "step by step instructions",
    "how to make",
    "how to hack",
    "write malware",
    "write a virus",
]

def blocklist_check(messages: list[str]) -> str:
    """Simple keyword blocklist — scores each message independently."""
    for msg in messages:
        lower = msg.lower()
        for keyword in BLOCKLIST_KEYWORDS:
            if keyword in lower:
                return "block"
    return "allow"


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def compute_metrics(tp: int, fp: int, tn: int, fn: int) -> dict:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)
    fpr       = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {
        "precision": round(precision, 4),
        "recall":    round(recall,    4),
        "f1":        round(f1,        4),
        "fpr":       round(fpr,       4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate():
    dataset_path = (
        pathlib.Path(__file__).parent / "datasets" / "benchmark_dataset.json"
    )
    dataset = json.loads(dataset_path.read_text())
    conversations = dataset["conversations"]

    print("=" * 60)
    print("SentinelGuard Benchmark Evaluation")
    print("=" * 60)
    print(f"Total conversations: {len(conversations)}")
    print(f"  Attack:  {sum(1 for c in conversations if c['label'] == 'attack')}")
    print(f"  Benign:  {sum(1 for c in conversations if c['label'] == 'benign')}")
    print()

    # --- Initialise SentinelGuard ---
    print("Loading SentinelGuard...")
    sg = SentinelGuard()
    print()

    # --- Run evaluation ---
    sg_tp = sg_fp = sg_tn = sg_fn = 0
    bl_tp = bl_fp = bl_tn = bl_fn = 0
    sg_latencies = []

    print(f"{'ID':<20} {'Label':<8} {'SG':<8} {'BL':<8} {'Risk':>6}  {'Attack type'}")
    print("-" * 70)

    for conv in conversations:
        session_id = conv["id"]
        messages   = conv["messages"]
        true_label = conv["label"]   # "attack" or "benign"

        # --- SentinelGuard ---
        sg.clear_session(session_id)
        start = time.perf_counter()
        sg_action = "allow"
        for msg in messages:
            result = sg.check(session_id, msg)
            if result.action in ("flag", "block"):
                sg_action = result.action
        elapsed = time.perf_counter() - start
        sg_latencies.append(elapsed * 1000)

        sg_detected = sg_action in ("flag", "block")

        # --- Blocklist baseline ---
        bl_result   = blocklist_check(messages)
        bl_detected = bl_result == "block"

        # --- Confusion matrix update ---
        if true_label == "attack":
            if sg_detected: sg_tp += 1
            else:           sg_fn += 1
            if bl_detected: bl_tp += 1
            else:           bl_fn += 1
        else:
            if sg_detected: sg_fp += 1
            else:           sg_tn += 1
            if bl_detected: bl_fp += 1
            else:           bl_tn += 1

        sg_label = "✓ DETECT" if sg_detected else "  allow"
        bl_label = "✓ DETECT" if bl_detected else "  allow"
        print(
            f"{conv['id']:<20} {true_label:<8} "
            f"{sg_label:<8} {bl_label:<8} "
            f"{result.risk_score:>6.3f}  {result.closest_attack}"
        )

    # --- Results ---
    sg_metrics = compute_metrics(sg_tp, sg_fp, sg_tn, sg_fn)
    bl_metrics = compute_metrics(bl_tp, bl_fp, bl_tn, bl_fn)
    avg_latency = sum(sg_latencies) / len(sg_latencies)

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"{'Metric':<25} {'SentinelGuard':>15} {'Blocklist':>12}")
    print("-" * 55)
    print(f"{'Precision':<25} {sg_metrics['precision']:>15.4f} {bl_metrics['precision']:>12.4f}")
    print(f"{'Recall':<25} {sg_metrics['recall']:>15.4f} {bl_metrics['recall']:>12.4f}")
    print(f"{'F1 Score':<25} {sg_metrics['f1']:>15.4f} {bl_metrics['f1']:>12.4f}")
    print(f"{'False Positive Rate':<25} {sg_metrics['fpr']:>15.4f} {bl_metrics['fpr']:>12.4f}")
    print(f"{'Avg latency (ms)':<25} {avg_latency:>15.1f} {'N/A':>12}")
    print()
    print(f"Confusion matrix — SentinelGuard:")
    print(f"  TP={sg_metrics['tp']}  FP={sg_metrics['fp']}  TN={sg_metrics['tn']}  FN={sg_metrics['fn']}")
    print(f"Confusion matrix — Blocklist:")
    print(f"  TP={bl_metrics['tp']}  FP={bl_metrics['fp']}  TN={bl_metrics['tn']}  FN={bl_metrics['fn']}")

    # --- Save results ---
    results_path = pathlib.Path(__file__).parent / "evaluation_results.json"
    results_path.write_text(json.dumps({
        "sentinelguard": sg_metrics,
        "blocklist_baseline": bl_metrics,
        "avg_latency_ms": round(avg_latency, 2),
    }, indent=2))
    print()
    print(f"Results saved to: {results_path}")


if __name__ == "__main__":
    evaluate()