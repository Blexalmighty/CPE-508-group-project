"""FastAPI service exposing the trained model to the OncoPredict frontend.

Run from the backend/ directory:

    uvicorn main:app --reload --port 8000

In development the Vite dev server proxies /api to port 8000, so the frontend
needs no CORS config. In production the frontend is a static host and calls
this service directly: set VITE_API_URL at build time, and ALLOWED_ORIGINS on
this side (comma-separated).

Authentication is configured by environment variables (STAFF_ID,
STAFF_PASSWORD, TOKEN_SECRET) -- a `.env` file next to this file is loaded at
startup. Without them the app refuses to start, and without a token /api/predict
returns 401. See backend/.env.example.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import auth
from registry import ModelUnavailable, registry
from schemas import HealthResponse, PatientRequest, PredictionResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("oncopredict")

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    registry.load()  # unpickling once at startup keeps requests fast
    yield


def _allowed_origins() -> list[str]:
    raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(title="OncoPredict Prediction Service", version="1.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,  # no cookies; the token travels as a header
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


class LoginRequest(BaseModel):
    staffId: str
    password: str


class LoginResponse(BaseModel):
    token: str
    staff: str


def _require_auth(staff: str = Depends(auth.authenticate)) -> str:
    return staff


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok" if registry.ready else "no-model",
        mode=registry.mode,
        detail=registry.detail,
    )


@app.post("/api/login", response_model=LoginResponse)
def login(credentials: LoginRequest):
    """Issue a signed token; the only endpoint reachable without one."""
    return LoginResponse(token=auth.login(credentials.staffId, credentials.password), staff=credentials.staffId)


@app.post("/api/predict", response_model=PredictionResponse)
def predict(patient: PatientRequest, staff: str = Depends(_require_auth)):
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
