import json
import joblib
from pathlib import Path

def load_model_and_features(models_dir: str = "/app/models"):
    models_path = Path(models_dir)

    model_path = models_path / "model.joblib"
    features_path = models_path / "features.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    if not features_path.exists():
        raise FileNotFoundError(f"Features config not found: {features_path}")

    model = joblib.load(model_path)

    with open(features_path, "r", encoding="utf-8") as f:
        features_payload = json.load(f)

    feature_cols = features_payload["feature_cols"]
    cat_cols = features_payload.get("cat_cols", [])

    model_version = features_payload.get("model_version")

    return model, feature_cols, cat_cols, model_version
