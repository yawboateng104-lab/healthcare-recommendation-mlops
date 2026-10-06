import os

import redis


REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]


redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_patient_features(patient_id: str) -> dict | None:
    key = f"patient_features:{patient_id}"
    features = redis_client.hgetall(key)

    if not features:
        return None

    return features
