# OncoPredict CDSS

React + Vite + Tailwind frontend for a Clinical Decision Support System, with a
FastAPI service that serves the trained model.

## Run it

Frontend:

```bash
npm install
npm run dev
```

Backend, from `backend/` — once per machine:

```bash
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Then each session:

```bash
.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8000
```

Open http://localhost:5173. Login is not real auth — any credentials get through.

Vite proxies `/api` to port 8000, so there's no CORS setup in development. Both
processes need to be running: there is no offline mock, because a fabricated
score that looks like a model output is worse than an error banner.

Python 3.12 rather than 3.14: the 3.14 wheels for pandas/scikit-learn/XGBoost
weren't available, so installing on 3.14 tries to compile from source.

## Which model is serving

The loader tries `random_forest_model.*`, then `model.*`, then
`xgb_Tumor_Response_model.*` — see [`backend/models/`](backend/models/).

Report §4.4 selects **Random Forest** as the deployment engine, and the loader
checks that name first, so dropping `random_forest_model.pkl` into
`backend/models/` and restarting uvicorn switches engines with no code change.

**Random Forest is in place and serving.** `/api/health` reports:

```
random_forest_model.pkl: Pipeline predicting Tumor_Response over 14 features
```

Fourteen, not fifteen: the RF was trained without `Overall_Survival_Months`,
excluded as leakage because it is a downstream outcome rather than a predictor.
The form still collects it — the XGBoost bundle does use it, and either model can
be serving — but under Random Forest it changes nothing, and the field says so.

It is a scikit-learn `Pipeline` (OneHotEncoder over the four `*_Code` columns,
passthrough for the rest) rather than a bundle dict, so the loader reads its
column order from `feature_names_in_`.

No single field moves the dashboard much: one feature at a time from a mid-point
patient, the largest swing is 0.056 (dosage), and metastasis alone moves it
0.001. Across 300 randomly drawn patients the favourable probability ranges
0.436–0.607 and the prediction lands on all four classes. If you want visible
movement in a demo, vary dosage, cancer type and stage together.

## What the model predicts

One target, `Tumor_Response`, in four classes encoded in clinical order:

| Code | Class |
| --- | --- |
| 0 | Progressive |
| 1 | Stable |
| 2 | Partial |
| 3 | Complete |

The dashboard's response figure is P(Partial) + P(Complete).

No treatment-completion model has been trained — all five candidate models
predict response. So `completionProbability` comes back `null` and the frontend
falls back to a rule-based estimate in
[`src/lib/predict.js`](src/lib/predict.js), badged "estimate" in the UI. Those
weights are invented and carry no clinical validity.

## API

**Request** — `POST /api/predict`. The first block feeds the model; bounds are
the documented valid ranges from report §3.1.2.

| Field | Type | Range / options |
| --- | --- | --- |
| `age` | number | 30–85 |
| `sex` | string | `Male`, `Female` |
| `tumorStage` | string | `I`, `II`, `III`, `IV` |
| `cancerType` | string | `Breast`, `Colon`, `Leukemia`, `Lung`, `Lymphoma` |
| `metastasisStatus` | string | `No`, `Yes` |
| `neutropenia` | string | `No`, `Yes` |
| `smokingStatus` | string | `Never`, `Former`, `Current` |
| `geneticMutation` | string | `None`, `BRCA1`, `EGFR`, `KRAS`, `TP53` |
| `chemoRegimen` | string | `None`, `ABVD`, `CHOP`, `FOLFOX`, `Gemcitabine` |
| `bmi` | number | 18.5–35.0 |
| `tumorSizeCm` | number | 1.0–10.0 |
| `dosage` | number | 50–600 |
| `cyclesCompleted` | number | 1–8 |
| `nauseaSeverity` | number | 1–5 |
| `survivalMonths` | number | 6–120 |

These are context only. Report §3.3 restricts them to routing supportive
interventions, so they never reach the model:

`location`, `religion`, `distanceKm`, `financialStatus`, `previousTreatment`,
`medicalHistory`

**Response**:

```json
{
  "responseProbability": 0.5525747776303311,
  "predictedClass": "Partial",
  "classProbabilities": {
    "Progressive": 0.1815, "Stable": 0.266,
    "Partial": 0.3225, "Complete": 0.2301
  },
  "completionProbability": null,
  "modelName": "random_forest_model.pkl",
  "target": "Tumor_Response"
}
```

Risk bands and recommendation text are derived in
[`src/lib/predict.js`](src/lib/predict.js) rather than in Python, so those rules
aren't duplicated across two languages.

The dropdown option strings in [`src/lib/fields.js`](src/lib/fields.js) are the
exact training categories, not labels — changing a value means changing
[`backend/features.py`](backend/features.py) to match.

### Checking it works

```bash
curl http://127.0.0.1:8000/api/health
```

`detail` names the file, estimator class, target, and feature count. An unknown
category comes back as a 422 naming the field and the categories it accepts.

## Structure

```
src/
  App.jsx                        state and layout shell
  components/
    LoginScreen.jsx
    PatientForm.jsx              renders sections from config
    Field.jsx                    one input, driven by a config entry
    ResultsDashboard.jsx         metric cards, class breakdown, recommendations
  lib/
    fields.js                    form schema: inputs, initial state, payload
    predict.js                   API call, risk bands, recommendation rules
backend/
  main.py                        FastAPI app and routes
  registry.py                    model discovery and probability extraction
  features.py                    form payload to feature frame (report 3.1.2)
  schemas.py                     request/response validation
  models/                        drop trained models here
```

## Current status

- Serves real predictions from Random Forest, the engine report §4.4 selects.
- Encoding verified against both saved copies of the XGBoost model, which agree
  to 15 decimal places.
- Form collects 15 model inputs — the superset both engines draw from, of which
  Random Forest uses 14 — with training categories and documented ranges enforced
  on both sides.
- Completion likelihood is a labelled rule-based estimate, not a model.
- Login is not real auth.
