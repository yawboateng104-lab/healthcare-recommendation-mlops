from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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
    features = get_patient_features(request.patient_id)

    if features is None:
        raise HTTPException(
            status_code=404,
            detail="Patient features not found",
        )

    try:
        prediction = model_service.predict(features)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid patient feature vector",
        ) from exc

    return {
        "patient_id": request.patient_id,
        "recommendation_class": prediction,
    }
