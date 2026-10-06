import os

import mlflow.pyfunc
import pandas as pd


MODEL_PATH = os.getenv("MODEL_PATH", "/app/model")

FEATURE_COLUMNS = [
    "claims_7d",
    "claims_30d",
    "claims_90d",
    "total_claim_amount_30d",
    "avg_claim_amount_30d",
    "rejected_claim_ratio_30d",
    "controlled_substance_ratio_30d",
    "refill_claim_ratio_30d",
    "cross_state_claim_ratio_30d",
    "avg_days_supply_30d",
    "avg_refill_number_30d",
]

COUNT_COLUMNS = [
    "claims_7d",
    "claims_30d",
    "claims_90d",
]


FLOAT_COLUMNS = [
    "total_claim_amount_30d",
    "avg_claim_amount_30d",
    "rejected_claim_ratio_30d",
    "controlled_substance_ratio_30d",
    "refill_claim_ratio_30d",
    "cross_state_claim_ratio_30d",
    "avg_days_supply_30d",
    "avg_refill_number_30d",
]


class ModelService:
    def __init__(self):
        self.model = None

    def load(self):
        self.model = mlflow.pyfunc.load_model(MODEL_PATH)

    def predict(self, features: dict) -> int:
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        row = {column: features[column] for column in FEATURE_COLUMNS}
        frame = pd.DataFrame([row], columns=FEATURE_COLUMNS)

        for column in COUNT_COLUMNS:
            frame[column] = frame[column].astype("int64")
        for column in FLOAT_COLUMNS:
            frame[column] = frame[column].astype("float64")

        prediction = self.model.predict(frame)

        return int(prediction[0])


model_service = ModelService()
