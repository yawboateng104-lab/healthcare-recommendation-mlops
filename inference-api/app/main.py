from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import time

from prometheus_client import Counter, Histogram, make_asgi_app

from app.model_service import model_service
from app.redis_client import get_patient_features


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_service.load()
    yield


app = FastAPI(
    title="Healthcare Recommendation Inference API",
    lifespan=lifespan,
)


REQUEST_COUNT = Counter(
    "healthcare_inference_requests_total",
    "Total prediction requests.",
)

ERROR_COUNT = Counter(
    "healthcare_inference_errors_total",
    "Total prediction errors.",
    ["status_code"],
)

PREDICTION_COUNT = Counter(
    "healthcare_prediction_total",
    "Total predictions by recommendation class.",
    ["class_id"],
)

INFERENCE_LATENCY = Histogram(
    "healthcare_inference_latency_seconds",
    "Prediction request latency in seconds.",
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


class PredictionRequest(BaseModel):
    patient_id: str


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": model_service.model is not None,
    }


@app.post("/predict")
def predict(request: PredictionRequest):
    REQUEST_COUNT.inc()
    start_time = time.perf_counter()

    try:
        features = get_patient_features(request.patient_id)

        if features is None:
            ERROR_COUNT.labels(status_code="404").inc()
            raise HTTPException(
                status_code=404,
                detail="Patient features not found",
            )

        try:
            prediction = model_service.predict(features)
        except (KeyError, TypeError, ValueError) as exc:
            ERROR_COUNT.labels(status_code="422").inc()
            raise HTTPException(
                status_code=422,
                detail="Invalid patient feature vector",
            ) from exc

        PREDICTION_COUNT.labels(
            class_id=str(prediction)
        ).inc()

        return {
            "patient_id": request.patient_id,
            "recommendation_class": prediction,
        }

    except HTTPException:
        raise

    except Exception:
        ERROR_COUNT.labels(status_code="500").inc()
        raise

    finally:
        INFERENCE_LATENCY.observe(
            time.perf_counter() - start_time
        )
