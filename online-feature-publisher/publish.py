import json
import os
import sys

import redis
import requests


DATABRICKS_HOST = os.environ["DATABRICKS_HOST"].rstrip("/")
DATABRICKS_CLIENT_ID = os.environ["DATABRICKS_CLIENT_ID"]
DATABRICKS_CLIENT_SECRET = os.environ["DATABRICKS_CLIENT_SECRET"]
WAREHOUSE_ID = os.environ["DATABRICKS_WAREHOUSE_ID"]

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]

TABLE = "workspace.gold.patient_features_online_snapshot"

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


def get_databricks_token():
    response = requests.post(
        f"{DATABRICKS_HOST}/oidc/v1/token",
        auth=(DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET),
        data={
            "grant_type": "client_credentials",
            "scope": "all-apis",
        },
        timeout=30,
    )

    response.raise_for_status()
    return response.json()["access_token"]


def query_snapshot():
    token = get_databricks_token()
    statement = f"""
        SELECT
            enterprise_patient_id,
            feature_timestamp,
            feature_contract_version,
            {", ".join(FEATURE_COLUMNS)}
        FROM {TABLE}
    """

    response = requests.post(
        f"{DATABRICKS_HOST}/api/2.0/sql/statements",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "warehouse_id": WAREHOUSE_ID,
            "statement": statement,
            "wait_timeout": "50s",
        },
        timeout=60,
    )

    response.raise_for_status()
    payload = response.json()

    state = payload.get("status", {}).get("state")

    if state != "SUCCEEDED":
        print(
            f"Databricks SQL statement failed: {json.dumps(payload.get('status'))}",
            file=sys.stderr,
        )
        sys.exit(1)

    columns = [
        column["name"]
        for column in payload["manifest"]["schema"]["columns"]
    ]

    rows = payload.get("result", {}).get("data_array", [])

    return columns, rows


def publish(columns, rows):
    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_connect_timeout=5,
    )

    client.ping()

    pipeline = client.pipeline(transaction=False)

    for row in rows:
        record = dict(zip(columns, row))

        patient_id = record.pop("enterprise_patient_id")

        mapping = {
            key: "" if value is None else str(value)
            for key, value in record.items()
        }

        pipeline.hset(
            f"patient_features:{patient_id}",
            mapping=mapping,
        )

    pipeline.execute()

    return len(rows)


def main():
    columns, rows = query_snapshot()

    if len(rows) != 1000:
        print(
            f"Expected 1000 rows but received {len(rows)}; refusing Redis publication",
            file=sys.stderr,
        )
        sys.exit(1)

    published = publish(columns, rows)

    print(f"ONLINE_FEATURE_ROWS_PUBLISHED={published}")


if __name__ == "__main__":
    main()
