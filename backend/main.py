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
import database
from registry import ModelUnavailable, registry
from schemas import HealthResponse, PatientRequest, PredictionResponse

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("oncopredict")

load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    registry.load()  # unpickling once at startup keeps requests fast
    try:
        database.init_db()
    except Exception as err:
        log.warning("Database init failed: %s", err)
    yield


def _allowed_origins() -> list[str]:
    raw = os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,https://cpe-508-group-project-tzlz.vercel.app",
    )
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


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int | None = None
    email: str | None = None
    name: str | None = None
    created_at: str | None = None


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


@app.post("/api/signup", response_model=LoginResponse)
def signup(payload: SignupRequest):
    db = database
    existing = db.get_user_auth(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")
    hash_hex, salt_hex = auth.hash_password(payload.password)
    try:
        db.create_user(payload.email, hash_hex, salt_hex, payload.name, is_admin=False)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {err}") from err
    token = auth._issue_token(payload.email)
    return LoginResponse(token=token, staff=payload.email)


@app.post("/api/user_login", response_model=LoginResponse)
def user_login(payload: UserLoginRequest):
    token = auth.user_login(payload.email, payload.password)
    return LoginResponse(token=token, staff=payload.email)


@app.get("/api/me", response_model=UserResponse)
def me(identity: str = Depends(_require_auth)):
    info = database.get_user_by_email(identity)
    if not info:
        return UserResponse(id=None, email=identity, name=None, created_at=None)
    return UserResponse(id=info.get("id"), email=info.get("email"), name=info.get("name"), created_at=str(info.get("created_at")))


@app.get("/api/my_records")
def my_records(identity: str = Depends(_require_auth)):
    """Return the authenticated user's prediction history."""
    try:
        recs = database.get_prediction_records_for_staff(identity)
    except Exception as err:
        log.exception("Failed to query records")
        raise HTTPException(status_code=500, detail="Could not fetch records") from err
    return {"records": recs}


@app.post("/api/logout")
def logout(authorization: str | None = None):
    """Explicit logout endpoint. The app clears session state client-side, but
    this endpoint validates any provided bearer token and returns a success
    message so the flow is intentional and inspectable in the API."""
    if authorization:
        try:
            auth.authenticate(authorization)
        except HTTPException:
            # A stale or already-invalid token should still count as a logout
            # attempt; the client will clear local state regardless.
            pass
    return {"ok": True, "message": "Logged out successfully."}


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

    # Persist the prediction linked to the authenticated identity (email or staff id)
    try:
        prediction_payload = {
            "predictedClass": predicted,
            "classProbabilities": by_class,
            "favourable": favourable,
            "modelName": registry.model.name,
            "target": registry.model.target,
        }
        database.save_prediction(staff, patient.model_dump(), prediction_payload)
    except Exception:
        log.exception("Failed to save prediction record")

    return PredictionResponse(
        responseProbability=favourable,
        predictedClass=predicted,
        classProbabilities=by_class,
        completionProbability=None,  # no completion model has been trained yet
        modelName=registry.model.name,
        target=registry.model.target,
    )
