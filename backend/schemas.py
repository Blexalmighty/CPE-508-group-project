"""Request and response shapes for the prediction API.

Numeric bounds are the documented valid ranges from report section 3.1.2 step 3.
They are enforced here rather than left to the scaler so an out-of-range value
comes back as a readable 422 instead of being silently clamped.
"""

from pydantic import BaseModel, Field


class PatientRequest(BaseModel):
    """Mirrors the payload built by toPayload() in src/lib/fields.js.

    The first block feeds the model. The second is context the model was never
    trained on -- it only routes the supportive recommendations, which is the
    separation report section 3.3 commits to.
    """

    age: int = Field(ge=30, le=85)
    sex: str
    tumorStage: str
    cancerType: str
    metastasisStatus: str
    neutropenia: str
    smokingStatus: str
    geneticMutation: str
    chemoRegimen: str
    bmi: float = Field(ge=18.5, le=35.0)
    tumorSizeCm: float = Field(ge=1.0, le=10.0)
    dosage: float = Field(ge=50.0, le=600.0)
    cyclesCompleted: int = Field(ge=1, le=8)
    nauseaSeverity: int = Field(ge=1, le=5)
    survivalMonths: float = Field(ge=6.0, le=120.0)

    location: str = ""
    religion: str = ""
    distanceKm: float = Field(default=0.0, ge=0)
    financialStatus: str = ""
    previousTreatment: str = ""
    medicalHistory: str = ""


class PredictionResponse(BaseModel):
    """What the model can actually say, and nothing more.

    completionProbability is null until a treatment-completion model exists --
    the trained models only predict Tumor_Response. The frontend labels that
    card as an estimate rather than inventing a number here.
    """

    responseProbability: float = Field(ge=0.0, le=1.0)
    predictedClass: str
    classProbabilities: dict[str, float]
    completionProbability: float | None = None
    modelName: str
    target: str


class HealthResponse(BaseModel):
    status: str
    mode: str
    detail: str
