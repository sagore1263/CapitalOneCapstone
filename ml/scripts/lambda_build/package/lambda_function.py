import json
from bisect import bisect_left
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "artifacts"

MODEL_PATH = ARTIFACT_DIR / "fraud_forest.json"
CDF_PATH = ARTIFACT_DIR / "fraud_cdf.json"
META_PATH = ARTIFACT_DIR / "feature_metadata.json"

forest = json.loads(MODEL_PATH.read_text())
cdf_data = json.loads(CDF_PATH.read_text())
metadata = json.loads(META_PATH.read_text())

FEATURE_NAMES = metadata["feature_names"]
sorted_probs = cdf_data["sorted_probs"]
cdf_values = cdf_data["cdf_values"]


def build_feature_vector(transaction: dict):
    values = []
    for name in FEATURE_NAMES:
        if name not in transaction:
            raise ValueError(f"Missing required feature: {name}")
        values.append(float(transaction[name]))
    return values


def predict_tree_probability(tree, features):
    node = 0
    children_left = tree["children_left"]
    children_right = tree["children_right"]
    feature = tree["feature"]
    threshold = tree["threshold"]
    value = tree["value"]

    while children_left[node] != children_right[node]:
        feat_idx = feature[node]
        if features[feat_idx] <= threshold[node]:
            node = children_left[node]
        else:
            node = children_right[node]

    counts = value[node]
    total = sum(counts)
    if total == 0:
        return 0.0
    return counts[1] / total


def predict_probability(features):
    probs = [predict_tree_probability(tree, features) for tree in forest["trees"]]
    return sum(probs) / len(probs)


def score_probability_to_percentile(prob: float) -> float:
    idx = bisect_left(sorted_probs, prob)
    if idx <= 0:
        return float(cdf_values[0])
    if idx >= len(sorted_probs):
        return float(cdf_values[-1])

    x0, x1 = sorted_probs[idx - 1], sorted_probs[idx]
    y0, y1 = cdf_values[idx - 1], cdf_values[idx]

    if x1 == x0:
        return float(y1)

    frac = (prob - x0) / (x1 - x0)
    return float(y0 + frac * (y1 - y0))


def parse_event(event: dict) -> dict:
    if "body" in event:
        body = event["body"]
        if isinstance(body, str):
            return json.loads(body)
        return body
    return event


def lambda_handler(event, context):
    try:
        payload = parse_event(event)
        transaction = payload["transaction"] if "transaction" in payload else payload

        features = build_feature_vector(transaction)
        pred_prob = float(predict_probability(features))
        fraud_score = score_probability_to_percentile(pred_prob)

        response = {
            "prediction_probability": pred_prob,
            "fraud_score": fraud_score,
            "feature_order": FEATURE_NAMES,
        }

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response),
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }