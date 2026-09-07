# OncoPredict CDSS Codebase Documentation

## 1. Project Overview

This project is a clinical decision support system for cancer care. It combines:

- a React + Vite frontend for entering patient information
- a FastAPI backend for authentication and prediction
- a trained ML model loaded from disk to estimate Tumor Response probability
- session-based login handled with a signed token in the browser

The app is meant to help clinicians assess the likely treatment response for a patient using structured clinical data.

The core idea is:

1. a staff member logs in
2. patient data is entered in the form
3. the frontend converts the inputs to the API payload
4. the backend validates the request and passes it to the model
5. the model returns class probabilities and a predicted class
6. the frontend converts the result into a dashboard with risk bands and recommendations

---

## 2. Technology Stack

### Frontend
- React 18
- Vite
- Tailwind CSS
- lucide-react icons

### Backend
- Python 3.12+
- FastAPI
- Pydantic validation
- scikit-learn / XGBoost models
- environment-based authentication

### Data model
- This project does not use a traditional database for its current core flow.
- Authentication is handled with environment variables and signed tokens.
- Model input mappings are defined in code, not stored in a DB.

---

## 3. Project Structure

```text
oncopredict-cdss/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── README.md
├── src/
│   ├── App.jsx
│   ├── index.css
│   ├── main.jsx
│   ├── components/
│   │   ├── Field.jsx
│   │   ├── LoginScreen.jsx
│   │   ├── PatientForm.jsx
│   │   └── ResultsDashboard.jsx
│   └── lib/
│       ├── api.js
│       ├── fields.js
│       ├── predict.js
│       └── session.js
├── backend/
│   ├── auth.py
│   ├── features.py
│   ├── main.py
│   ├── registry.py
│   ├── schemas.py
│   ├── .env.example
│   ├── .env
│   └── models/
│       └── trained model files
├── docs/
│   └── INTEGRATION_NOTES.md
└── README.md
```

---

## 4. Frontend Architecture

### 4.1 App Shell
File: [src/App.jsx](../src/App.jsx)

This is the main app state container. It does the following:

- checks if a valid token exists in localStorage
- displays the login form when no user is authenticated
- displays the patient form and dashboard when the user is authenticated
- handles logout
- submits patient data to the prediction API

Primary responsibilities:

- `user` state: tracks the logged-in staff user
- `form` state: stores patient form data
- `result` state: stores the prediction result returned by backend
- `handleSubmit`: sends the payload to the prediction route
- `signOut`: clears session credentials and resets app state

Why this function matters:
- it controls page flow between login and clinical dashboard
- it prevents a stale dashboard from staying visible after a session expires

---

### 4.2 Login Screen
File: [src/components/LoginScreen.jsx](../src/components/LoginScreen.jsx)

This component renders the login UI and handles the credential submission.

Key behavior:

- captures `staffId` and `password`
- calls `login(staffId, password)` from the session module
- stores the token in localStorage on success
- shows an error banner for invalid credentials or failed fetches

Important functions:

- `handleSubmit`: async function that tries to authenticate the user
- `LoginField`: reusable input component for the login form

Why this exists:
- the server is protected behind token-based auth
- the UI must present the login before any patient data is submitted

---

### 4.3 Form Definition and Payload Building
File: [src/lib/fields.js](../src/lib/fields.js)

This file is the single source of truth for the patient form.

It defines:

- `SECTIONS`: grouped form fields by domain
- `INITIAL_FORM`: default values for every field
- `toPayload(form)`: converts field values into the exact shape expected by the backend

Important functions:

- `toPayload(form)`: ensures numeric values are numbers, not strings
- `INITIAL_FORM`: provides consistent starting state for a new patient record

Why this file matters:
- changing field names, option values, or ranges here directly affects the UI and backend contract
- the app assumes the frontend and backend use the same feature names and categories

---

### 4.4 Prediction Client and Risk Logic
File: [src/lib/predict.js](../src/lib/predict.js)

This is the main AI result handling module.

Key functions:

- `predictOutcome(patient)`: orchestrates the prediction call and prepares all UI data
- `fetchPrediction(patient)`: posts the patient payload to `/api/predict`
- `orderClasses(probabilities)`: arranges class names in the clinical order
- `riskBand(score)`: maps a numerical score to a risk label
- `estimateCompletion(patient)`: fallback estimate when no completion model exists
- `buildRecommendations(patient, completion, response)`: builds decision-support text

Why these functions matter:
- the backend model can only predict Tumor Response probability
- the frontend builds human-friendly recommendations, risk classes, and compliance messaging
- the app does not invent model outputs; it surfaces real model output or a clearly labeled estimate

---

### 4.5 HTTP Wrapper and Session helpers
File: [src/lib/api.js](../src/lib/api.js)

This is the fetch client used by all backend requests.

Key functions:

- `apiRequest(path, options)`: wraps `fetch` and adds JSON handling
- `describeError(body)`: formats backend validation errors into readable text
- `ApiError`: custom error object storing HTTP status codes

Why it exists:
- all backend calls go through one place
- 401/403 handling is centralized
- auth errors can trigger the logout flow cleanly

File: [src/lib/session.js](../src/lib/session.js)

This module stores and reads the login token.

Key functions:

- `login(staffId, password)`: posts credentials and saves token
- `getToken()`: returns the current session token
- `getStaff()`: returns the signed-in staff member
- `clearSession()`: clears the browser session

Why it exists:
- the app persists login across page reloads
- expired or invalid tokens are handled by clearing the session and forcing re-login

---

## 5. Backend Architecture

### 5.1 API Entry Point
File: [backend/main.py](../backend/main.py)

This is the FastAPI application entry point.

It defines:

- CORS configuration for browser access
- the app startup lifecycle
- routes for `/api/health`, `/api/login`, and `/api/predict`

Key pieces:

- `app = FastAPI(...)`: creates the application
- `_allowed_origins()`: reads the allowed frontend origins from environment
- `lifespan`: runs setup logic when the server starts
- `login(credentials: LoginRequest)`: issues a signed auth token
- `predict(patient: PatientRequest, staff: str = Depends(_require_auth))`: runs model inference

Why this is needed:
- the browser cannot call the backend directly without CORS rules
- the prediction endpoint must require a valid token before it processes patient data

---

### 5.2 Authentication System
File: [backend/auth.py](../backend/auth.py)

This file manages access control.

Key functions:

- `config()`: loads `STAFF_ID`, `STAFF_PASSWORD`, and `TOKEN_SECRET` from environment
- `login(staff_id, password)`: validates credentials and returns a signed token
- `authenticate(authorization)`: validates `Authorization: Bearer <token>` on protected API calls

Why it exists:
- the backend uses a single shared credential model for demonstration purposes
- the token is HMAC-signed and time-limited
- unauthorized requests fail with 401 instead of processing patient data

This is intentionally simple and not a production-grade auth system.

---

### 5.3 Model Loader and Registry
File: [backend/registry.py](../backend/registry.py)

This file discovers and loads the trained model file.

Key classes and functions:

- `ModelUnavailable`: exception raised when no usable model is found
- `LoadedModel`: wrapper around the estimator and the feature names it expects
- `BoosterAdapter`: adapts native XGBoost boosters to the prediction API shape
- `Registry`: loads the model and exposes the prediction logic
- `_pick_file()`: finds the best model file in the models directory
- `_load(path)`: loads the model from disk
- `_unwrap(payload)`: unwraps saved dict bundles or estimator objects
- `registry.predict(patient)`: generates probabilities and class label

Why it matters:
- the project does not hardcode one model file name permanently
- the app tries preferred model names in order so deployment can switch cleanly
- the backend executes the actual prediction and returns confidence values

---

### 5.4 Feature Mapping and Input Transformation
File: [backend/features.py](../backend/features.py)

This file converts a patient form payload into the exact feature matrix the model was trained on.

Key functions:

- `build_frame(patient, columns)`: builds a one-row DataFrame in the exact column order the model expects
- `_encode(patient)`: maps text values and numeric inputs into numeric encodings
- `_code(field, mapping, value)`: validates categorical values against known model categories
- `_min_max(name, value)`: reproduces the MinMax scaling used during training
- `slug(column)`: maps model column names to the internal dictionary keys

Why it matters:
- ML models need numeric columns in a very specific order and encoding
- even a small mismatch in a category label or feature shape can produce wrong results
- this file is the bridge between the UI and the model

Important design choice:
- the model does not receive raw strings
- every value is converted into the category codes and scaled values the model expects

---

### 5.5 API Validation Models
File: [backend/schemas.py](../backend/schemas.py)

This file defines Pydantic request and response models.

Key models:

- `PatientRequest`: validation schema for patient submission
- `PredictionResponse`: expected response from `/api/predict`
- `HealthResponse`: status details for `/api/health`

Why it matters:
- invalid values fail early with useful 422 or 400 errors
- the frontend and backend share a predictable contract
- out-of-range patient values are rejected before hitting the model

---

## 6. Runtime Flow

### Login flow
1. The user enters staff ID and password in [src/components/LoginScreen.jsx](../src/components/LoginScreen.jsx)
2. `login()` in [src/lib/session.js](../src/lib/session.js) posts to `/api/login`
3. [backend/main.py](../backend/main.py) calls `auth.login()`
4. if credentials match, a signed token is returned
5. the token is stored in localStorage
6. the app unlocks the patient dashboard

### Prediction flow
1. The user fills the patient form defined in [src/lib/fields.js](../src/lib/fields.js)
2. `toPayload()` ensures numbers are cast correctly
3. `predictOutcome()` in [src/lib/predict.js](../src/lib/predict.js) sends the payload to `/api/predict`
4. [backend/main.py](../backend/main.py) validates the request and checks auth
5. [backend/registry.py](../backend/registry.py) loads the model and predicts class probabilities
6. [backend/features.py](../backend/features.py) converts the patient fields into the exact training feature space
7. the frontend converts the response into risk labels and recommendations

---

## 7. Why These Functions Are Used

### Why `apiRequest()` is used
Because all backend calls should go through a single consistent wrapper:
- adds headers
- serializes JSON
- handles HTTP failures
- converts backend errors into readable UI messages

### Why `toPayload()` is used
Because form values arrive as strings from the browser. The model expects numbers and exact value types.

### Why `build_frame()` is used
Because the model expects a DataFrame with a very specific column order and encoding. Without this, the model receives mismatched features and produces invalid or nonsensical predictions.

### Why `auth.login()` is used
Because the backend must protect patient data and prediction results from unauthenticated access.

### Why `Registry.predict()` is used
Because the model file is not loaded directly into the app. The code abstracts the logic so the project can swap models safely and still use the same API contract.

### Why `estimateCompletion()` exists
Because the trained models only predict Tumor Response. The dashboard still shows a completion estimate, but it is explicitly labeled as a rule-based estimate and not a model output.

---

## 8. Environment Variables

### Required for backend auth
- `STAFF_ID`
- `STAFF_PASSWORD`
- `TOKEN_SECRET`

### Optional for deployment
- `ALLOWED_ORIGINS`: comma-separated frontend URL(s)
- `DATABASE_URL`: if database persistence is later added

These values are expected in [backend/.env.example](../backend/.env.example).

---

## 9. Important Caveats

- The project is not using a database in the current working version.
- The upload and prediction process is tied to the model file stored in `backend/models/`.
- The app uses a single shared login credential, not a real multi-user account system.
- The completion estimate is not a real ML model; it is a rule-based approximation.
- The model input schema and the frontend form must stay in sync.

---

## 10. How to Run the Project

### Frontend
```bash
npm install
npm run dev
```

### Backend
From the backend directory:

```bash
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m uvicorn main:app --reload --port 8000
```

### Environment setup
Copy the example file and fill values:

```bash
copy .env.example .env
```

Then set:
- `STAFF_ID`
- `STAFF_PASSWORD`
- `TOKEN_SECRET`

---

## 11. Summary

This project is essentially a small AI-powered clinical dashboard built with:

- a frontend form for collecting patient data
- a backend API for auth and prediction
- a model registry that loads the trained estimator from disk
- encoding logic that transforms clinical values into model-ready inputs
- a front-end risk dashboard that makes model results readable for clinicians

The most important files to read first are:

- [src/App.jsx](../src/App.jsx)
- [src/lib/fields.js](../src/lib/fields.js)
- [src/lib/predict.js](../src/lib/predict.js)
- [backend/main.py](../backend/main.py)
- [backend/features.py](../backend/features.py)
- [backend/registry.py](../backend/registry.py)
- [backend/auth.py](../backend/auth.py)

These files describe the app’s actual logic and explain why each function exists.
