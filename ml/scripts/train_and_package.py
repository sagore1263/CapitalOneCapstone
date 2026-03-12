import json
from pathlib import Path

import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42
N_SAMPLES = 5000
N_FEATURES = 5

FEATURE_NAMES = [
    "amount",
    "hour",
    "is_international",
    "merchant_risk",
    "txn_count_24h",
]

BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR.parent / "artifacts"


def export_tree(estimator):
    t = estimator.tree_
    return {
        "children_left": t.children_left.tolist(),
        "children_right": t.children_right.tolist(),
        "feature": t.feature.tolist(),
        "threshold": t.threshold.tolist(),
        "value": t.value.squeeze(axis=1).tolist(),  # [n_nodes][n_classes]
    }


def export_forest(model):
    return {
        "model_type": "RandomForestClassifier",
        "n_classes": int(model.n_classes_),
        "n_features_in": int(model.n_features_in_),
        "classes": model.classes_.tolist(),
        "trees": [export_tree(est) for est in model.estimators_],
    }


def main():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    X, y = make_classification(
        n_samples=N_SAMPLES,
        n_features=N_FEATURES,
        n_informative=4,
        n_redundant=0,
        n_clusters_per_class=1,
        weights=[0.92, 0.08],
        random_state=RANDOM_STATE,
    )

    X = X.copy()
    X[:, 0] = np.abs(X[:, 0] * 200)
    X[:, 1] = np.clip((X[:, 1] * 6 + 12), 0, 23)
    X[:, 2] = (X[:, 2] > 0).astype(int)
    X[:, 3] = np.clip((X[:, 3] * 20 + 50), 0, 100)
    X[:, 4] = np.clip((X[:, 4] * 3 + 5), 0, 20)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=RANDOM_STATE
    )

    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=10,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    test_probs = model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)

    auc = roc_auc_score(y_test, test_probs)
    print(f"Test ROC AUC: {auc:.4f}")
    print(classification_report(y_test, test_preds))

    all_probs = model.predict_proba(X)[:, 1]
    sorted_probs = np.sort(all_probs)
    cdf_values = (np.arange(1, len(sorted_probs) + 1) / len(sorted_probs)).tolist()

    forest_path = ARTIFACT_DIR / "fraud_forest.json"
    cdf_path = ARTIFACT_DIR / "fraud_cdf.json"
    meta_path = ARTIFACT_DIR / "feature_metadata.json"

    forest_path.write_text(json.dumps(export_forest(model)))
    cdf_path.write_text(json.dumps({
        "sorted_probs": sorted_probs.tolist(),
        "cdf_values": cdf_values,
    }))
    meta_path.write_text(json.dumps({
        "feature_names": FEATURE_NAMES,
        "model_type": "RandomForestClassifier",
        "notes": "Pure-Python exported forest for Lambda scoring demo",
    }, indent=2))

    print(f"Saved forest to {forest_path}")
    print(f"Saved CDF to   {cdf_path}")
    print(f"Saved meta to  {meta_path}")


if __name__ == "__main__":
    main()