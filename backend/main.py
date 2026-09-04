"""FastAPI service exposing the trained model to the OncoPredict frontend.

Run from the backend/ directory:

    uvicorn main:app --reload --port 8000

The Vite dev server proxies /api to port 8000, so the frontend needs no CORS
config in development.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from registry import ModelUnavailable, registry
from schemas import HealthResponse, PatientRequest, PredictionResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("oncopredict")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    registry.load()  # unpickling once at startup keeps requests fast
    yield


app = FastAPI(title="OncoPredict Prediction Service", version="1.0.0", lifespan=lifespan)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok" if registry.ready else "no-model",
        mode=registry.mode,
        detail=registry.detail,
    )


@app.post("/api/predict", response_model=PredictionResponse)
def predict(patient: PatientRequest):
    if not registry.ready:
        raise HTTPException(status_code=503, detail=registry.detail)

    try:
        predicted, by_class, favourable = registry.predict(patient)
    except ModelUnavailable as err:
        raise HTTPException(status_code=503, detail=str(err)) from err
    except ValueError as err:
        # A category or column the training frame did not have. features.py says
        # exactly which one, so pass that through rather than a bare 422.
        raise HTTPException(status_code=422, detail=str(err)) from err
    except Exception as err:
        log.exception("Prediction failed")
        raise HTTPException(
            status_code=500,
            detail=f"Model rejected the feature frame: {err}",
        ) from err

    return PredictionResponse(
        responseProbability=favourable,
        predictedClass=predicted,
        classProbabilities=by_class,
        completionProbability=None,  # no completion model has been trained yet
        modelName=registry.model.name,
        target=registry.model.target,
    )
