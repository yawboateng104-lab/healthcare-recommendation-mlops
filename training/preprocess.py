import json
from pathlib import Path

CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "features"
    / "patient_feature_contract_v1.json"
)

with open(CONTRACT_PATH, "r") as f:
    feature_contract = json.load(f)

FEATURE_COLUMNS = list(feature_contract["features"].keys())

print("Contract:", feature_contract["name"])
print("Version:", feature_contract["version"])
print("Features:", FEATURE_COLUMNS)
