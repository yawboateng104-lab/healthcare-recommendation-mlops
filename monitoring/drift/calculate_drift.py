import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import wasserstein_distance


REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACT_PATH = (
    REPO_ROOT
    / "features"
    / "patient_feature_contract_v1.json"
)

REFERENCE_TABLE = (
    "workspace.gold.patient_recommendation_training_30d"
)

CURRENT_TABLE = (
    "workspace.gold.patient_features_online_snapshot"
)

TRAINING_CUTOFF = "2026-08-03T07:24:58.991Z"

DATABRICKS_HOST = os.environ["DATABRICKS_HOST"].rstrip("/")
DATABRICKS_CLIENT_ID = os.environ["DATABRICKS_CLIENT_ID"]
DATABRICKS_CLIENT_SECRET = os.environ["DATABRICKS_CLIENT_SECRET"]
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]


def load_feature_names():
    with CONTRACT_PATH.open() as f:
        contract = json.load(f)

    return list(contract["features"].keys())


def get_databricks_token():
    response = requests.post(
        f"{DATABRICKS_HOST}/oidc/v1/token",
        auth=(
            DATABRICKS_CLIENT_ID,
            DATABRICKS_CLIENT_SECRET,
        ),
        data={
            "grant_type": "client_credentials",
            "scope": "all-apis",
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["access_token"]


def execute_query(statement, token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        f"{DATABRICKS_HOST}/api/2.0/sql/statements",
        headers=headers,
        json={
            "warehouse_id": WAREHOUSE_ID,
            "statement": statement,
            "wait_timeout": "50s",
            "disposition": "INLINE",
        },
        timeout=60,
    )

    response.raise_for_status()
    payload = response.json()

    state = payload.get("status", {}).get("state")

    if state != "SUCCEEDED":
        print(
            "Databricks SQL status:",
            payload.get("status"),
            file=sys.stderr,
        )
        raise RuntimeError(
            f"Databricks SQL statement state was {state}"
        )

    columns = [
        column["name"]
        for column in payload["manifest"]["schema"]["columns"]
    ]

    result = payload.get("result", {})
    rows = list(result.get("data_array", []))

    statement_id = payload["statement_id"]
    next_chunk_index = result.get("next_chunk_index")

    while next_chunk_index is not None:
        chunk_response = requests.get(
            f"{DATABRICKS_HOST}/api/2.0/sql/statements/"
            f"{statement_id}/result/chunks/{next_chunk_index}",
            headers=headers,
            timeout=60,
        )

        chunk_response.raise_for_status()
        chunk = chunk_response.json()

        rows.extend(chunk.get("data_array", []))
        next_chunk_index = chunk.get("next_chunk_index")

    expected_rows = payload.get("manifest", {}).get(
        "total_row_count"
    )

    if expected_rows is not None and len(rows) != expected_rows:
        raise RuntimeError(
            f"Incomplete Databricks result: expected "
            f"{expected_rows} rows, received {len(rows)}"
        )

    return pd.DataFrame(rows, columns=columns)


def load_populations(feature_names):
    token = get_databricks_token()

    feature_sql = ", ".join(feature_names)

    reference_query = f"""
        SELECT {feature_sql}
        FROM {REFERENCE_TABLE}
        WHERE feature_timestamp <= TIMESTAMP '{TRAINING_CUTOFF}'
        ORDER BY feature_timestamp, enterprise_patient_id
        LIMIT 268293
    """

    current_query = f"""
        SELECT {feature_sql}
        FROM {CURRENT_TABLE}
    """

    reference_df = execute_query(reference_query, token)
    current_df = execute_query(current_query, token)

    return reference_df, current_df


def calculate_psi(reference, current, bins=10):
    reference = np.asarray(reference, dtype=float)
    current = np.asarray(current, dtype=float)

    reference = reference[np.isfinite(reference)]
    current = current[np.isfinite(current)]

    if len(reference) == 0 or len(current) == 0:
        return np.nan

    boundaries = np.unique(
        np.quantile(
            reference,
            np.linspace(0, 1, bins + 1),
        )
    )

    if len(boundaries) < 2:
        return (
            0.0
            if np.all(current == reference[0])
            else np.inf
        )

    boundaries[0] = -np.inf
    boundaries[-1] = np.inf

    reference_counts, _ = np.histogram(
        reference,
        bins=boundaries,
    )

    current_counts, _ = np.histogram(
        current,
        bins=boundaries,
    )

    reference_pct = reference_counts / len(reference)
    current_pct = current_counts / len(current)

    epsilon = 1e-6

    reference_pct = np.clip(
        reference_pct,
        epsilon,
        None,
    )

    current_pct = np.clip(
        current_pct,
        epsilon,
        None,
    )

    return float(
        np.sum(
            (current_pct - reference_pct)
            * np.log(current_pct / reference_pct)
        )
    )


def main():
    feature_names = load_feature_names()

    print("FEATURE_COUNT:", len(feature_names))

    reference_df, current_df = load_populations(
        feature_names
    )

    print("REFERENCE_ROWS:", len(reference_df))
    print("CURRENT_ROWS:", len(current_df))
    print()

    results = []

    for feature in feature_names:
        reference_values = pd.to_numeric(
            reference_df[feature],
            errors="coerce",
        ).to_numpy()

        current_values = pd.to_numeric(
            current_df[feature],
            errors="coerce",
        ).to_numpy()

        reference_clean = reference_values[
            np.isfinite(reference_values)
        ]

        current_clean = current_values[
            np.isfinite(current_values)
        ]

        psi = calculate_psi(
            reference_clean,
            current_clean,
        )

        wasserstein = wasserstein_distance(
            reference_clean,
            current_clean,
        )

        results.append(
            {
                "feature": feature,
                "psi": psi,
                "wasserstein": float(wasserstein),
            }
        )

    results_df = pd.DataFrame(results)

    print(
        results_df.to_string(
            index=False,
            float_format=lambda x: f"{x:.6f}",
        )
    )


if __name__ == "__main__":
    main()
