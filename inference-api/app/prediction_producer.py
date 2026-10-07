import json
import logging
import os
import uuid
from datetime import datetime, timezone

from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer


log = logging.getLogger(__name__)

TOPIC = os.getenv(
    "PREDICTION_TOPIC",
    "healthcare-predictions.v1",
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "workspace.ml.healthcare_recommendation_30d_model",
)
MODEL_VERSION = os.getenv("MODEL_VERSION", "1")

SCHEMA_PATH = os.getenv(
    "PREDICTION_SCHEMA_PATH",
    "/app/contracts/healthcare_prediction_event_v1.avsc",
)

_producer = None


def _get_producer():
    global _producer

    if _producer is not None:
        return _producer

    bootstrap_servers = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
    schema_registry_url = os.environ["SCHEMA_REGISTRY_URL"]

    with open(SCHEMA_PATH) as f:
        schema_str = json.dumps(json.load(f))

    schema_registry_client = SchemaRegistryClient(
        {"url": schema_registry_url}
    )

    avro_serializer = AvroSerializer(
        schema_registry_client,
        schema_str,
        conf={"auto.register.schemas": False},
    )

    _producer = SerializingProducer(
        {
            "bootstrap.servers": bootstrap_servers,
            "key.serializer": StringSerializer("utf_8"),
            "value.serializer": avro_serializer,
            "acks": "all",
            "enable.idempotence": True,
        }
    )

    return _producer


def _delivery_report(err, msg):
    if err is not None:
        log.error(
            "prediction_event_delivery_failed",
            extra={"error": str(err)},
        )


def publish_prediction(
    enterprise_patient_id: str,
    predicted_class: int,
    feature_timestamp: str | None,
    feature_contract_version: str,
) -> str:
    prediction_id = str(uuid.uuid4())

    event = {
        "prediction_id": prediction_id,
        "event_type": "healthcare_prediction",
        "event_version": 1,
        "enterprise_patient_id": enterprise_patient_id,
        "prediction_timestamp": datetime.now(timezone.utc),
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_contract_version": feature_contract_version,
        "feature_timestamp": (
            datetime.fromisoformat(
                feature_timestamp.replace("Z", "+00:00")
            )
            if feature_timestamp
            else None
        ),
        "predicted_class": int(predicted_class),
    }

    producer = _get_producer()
    producer.produce(
        topic=TOPIC,
        key=enterprise_patient_id,
        value=event,
        on_delivery=_delivery_report,
    )

    producer.poll(0)

    return prediction_id
