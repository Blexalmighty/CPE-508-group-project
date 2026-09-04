# Integration notes

What changed when the trained model was wired into the app, why Random Forest is
the right engine, and what is still open. Written 2026-09-04.

## 1. The model is live

`POST /api/predict` calls the real trained model. There is no mock and no
fallback path — `USE_MOCK` and the placeholder score generator are gone. A failed
call surfaces as a red error banner naming the reason, because a fabricated score
that looks like a model output is worse than an error.

Verified end to end in the browser: 21 form fields submit, the request returns
200 OK with `responseProbability 0.5525747776303311`, and the dashboard renders
Response 55%, Completion 55% (badged "estimate"), and a four-class breakdown of
18 / 27 / 32 / 23%. No console errors.

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

```
{"status":"ok","mode":"loaded",
 "detail":"random_forest_model.pkl: Pipeline predicting Tumor_Response over 14 features"}
```

Random Forest is the engine serving — see §4. Where this document quotes XGBoost
numbers, they are the earlier run kept for comparison, and labelled as such.

## 2. What the file on disk actually contained

`model.pkl` is not a bare estimator. It is a bundle:

```python
{"model": <XGBClassifier>, "feature_columns": [...15 names...], "target": "Tumor_Response"}
```

`registry.py` now unwraps that dict before use, and builds its feature frame from
the column list **the file itself declares** rather than a list hardcoded in
Python. That is what makes the Random Forest swap a no-code-change operation: if
Jedidiah's model was trained on the same 15 columns in a different order, it
still works.

The 15 columns, as declared by the bundle:

```
Sex  Tumor_Stage  Metastasis_Status  Neutropenia  Overall_Survival_Months
Smoking_Status_Code  Cancer_Type_Code  Genetic_Mutation_Code
Chemotherapy_Regimen_Code  Age_scaled  BMI_scaled  Tumor_Size_scaled
Dosage (mg/m²)_scaled  Cycles_Completed_scaled  Nausea_Severity_scaled
```

Note the `²` in `Dosage (mg/m²)_scaled`. Matching column names literally is
fragile with a non-ASCII character in play, so `features.py` matches on a slug
(lowercase, strip `_scaled`/`_Code`, drop non-alphanumerics).

## 3. Preprocessing is reproduced, and verified — not assumed

`features.py` mirrors report §3.1.2 exactly: the 0/1 maps, the ordinal stage map,
the four `LabelEncoder` lookups, and min-max scaling over the documented ranges.
`Overall_Survival_Months` is a feature but was never scaled in training, so it
goes in raw.

This is the part of the system where a mistake does not raise an error — it
produces confident wrong numbers. So it was checked rather than trusted:
`model.pkl` and `xgb_Tumor_Response_model.json` are the same trained model saved
two different ways. Feeding both through `features.build_frame` produces
**identical probabilities, max absolute difference 0.0**. Had the encoding been
wrong, the two serializations would have disagreed.

If anyone retrains with different encodings, `features.py` must change to match.

## 4. Random Forest is the better model — you read the report correctly

From Table 1 (10,465-patient holdout test set):

| Algorithm | Accuracy | Weighted F1 | Macro F1 |
| --- | --- | --- | --- |
| Logistic Regression | 0.3999 | 0.2285 | 0.1428 |
| Decision Tree | 0.3027 | 0.3040 | 0.2549 |
| **Random Forest** | 0.3380 | **0.3082** | 0.2366 |
| SVM (RBF) | 0.2692 | 0.2783 | 0.2222 |
| XGBoost | 0.3915 | 0.2173 | 0.1737 |

Accuracy is the wrong column to read, and that is the whole story. Partial
Response is 4,185 / 10,465 = **39.99%** of the test set. So a model that ignores
every input and always answers "Partial" scores 39.99% accuracy.

That is literally what Logistic Regression did — the report calls it the Accuracy
Paradox. Its confusion matrix is every patient in one column, 0.00 recall on
Progressive, Stable and Complete. Highest accuracy in the study, useless as a
clinical tool.

XGBoost — the model currently serving — is a milder version of the same failure:

| Class | Recall | Correct / Support |
| --- | --- | --- |
| Progressive | 0.0000 | 0 / 1,042 |
| Stable | 0.0819 | 257 / 3,138 |
| Partial | 0.9154 | 3,831 / 4,185 |
| Complete | 0.0043 | 9 / 2,100 |

It predicted Partial for 9,532 of 10,465 patients. It never once identified a
Progressive patient. Progressive is the class that matters most for
risk-flagging — those are the patients whose therapy is failing.

Random Forest catches 21 Progressive and 253 Complete. Small numbers, but the
model is at least answering the question across all four categories, which is why
it takes the highest weighted F1 (0.3082) and why §4.4 selects it:

> "Random Forest (random_forest_model.pkl) is selected as the primary engine for
> Task 7 web application integration."

So: RF is best on the metric the report itself nominated as primary (§3.4,
Weighted F1). Worth stating plainly to whoever presents this — **RF wins because
it is the least degenerate, not because it is accurate.** Every model in the
table is at or below the 39.99% majority-class baseline. Decision Tree actually
beats RF on Macro F1 (0.2549 vs 0.2366), the metric that weights all four classes
equally, so "RF is the winner" holds on weighted F1 but is not unanimous.

### The backend already prefers it

`registry.py` tries filenames in this order:

```
random_forest_model.*      <- checked first, per report 4.4
model.*                    <- the XGBoost bundle, currently serving
xgb_Tumor_Response_model.*
```

Jedidiah's file arrived on 2026-09-04 and **is now serving**:

```
random_forest_model.pkl: Pipeline predicting Tumor_Response over 14 features
```

Its recorded metrics match report Table 1 exactly — accuracy 0.33798, weighted F1
0.30818, best params `max_depth=15, min_samples_leaf=4, n_estimators=300` — so the
file on disk is the same model the report benchmarked, not a re-run.

### Two differences from the XGBoost bundle

**It is a `Pipeline`, not a bundle dict.** `random_forest_train.py` saves
`rf_best` directly, so there is no `feature_columns` key. The loader falls back to
`feature_names_in_`, which scikit-learn populates because the pipeline was fitted
on a DataFrame. Steps: `OneHotEncoder(handle_unknown="ignore")` over the four
`*_Code` columns, `passthrough` for the remaining ten.

`handle_unknown="ignore"` is worth noting — an unseen category becomes an all-zero
one-hot block rather than an error. The request schema rejects unknown categories
before they reach the model, so this should never trigger, but it means a
mismatch would fail silently rather than loudly.

**It uses 14 features, not 15.** Jedidiah excluded
`Overall_Survival_Months`, with this comment in the training script:

> `Overall_Survival_Months (leakage risk - it's a downstream outcome, not a predictor)`

That is the same concern §6 of this document raises independently. He was right,
and the RF is the better-specified model for it.

Because `build_frame` constructs exactly the columns the loaded model declares,
this needed no backend change. Confirmed empirically: sweeping `survivalMonths`
from 6 to 120 moves the RF output by **exactly 0.0000**. The form still collects
the field, since the XGBoost bundle does use it and either model can serve, but it
now carries the hint "Recorded for context. Excluded from the Random Forest model
as leakage." A live input that silently does nothing is worse than a labelled one.

### One loader bug this exposed

`_unwrap` read the column list as:

```python
columns = list(getattr(estimator, "feature_names_in_", None) or [])
```

`feature_names_in_` is a NumPy array, and `or` on an array raises *"The truth
value of an array with more than one element is ambiguous."* The bundle-dict path
never hit it because that yields a plain list; this Pipeline was the first bare
estimator to reach the line. Fixed by testing for `None` explicitly instead of
relying on truthiness, in both branches of `_unwrap`.

### Verified after the swap

- `/api/health` names `random_forest_model.pkl`
- Browser POST returns 200 OK, `responseProbability 0.5525747776303311`, and the
  dashboard shows a 18 / 27 / 32 / 23% breakdown — visibly more spread than
  XGBoost's 11 / 29 / 41 / 20%, which is exactly the behaviour §4.4 selected it for
- Over 300 random patients: favourable probability 0.436–0.607, and **all four
  classes appear as predictions** (Partial 177, Stable 57, Complete 52,
  Progressive 14). XGBoost never predicted Progressive at all.
- No console errors

## 5. How much the serving model responds to input

Measured against the live API with Random Forest loaded, because this determines
whether a demo looks convincing. One feature at a time from a mid-point patient:

| Feature | Swing (RF) | Swing (XGBoost) |
| --- | --- | --- |
| Dosage | 0.056 | 0.017 |
| Cancer type | 0.041 | 0.009 |
| Tumour stage | 0.034 | 0.024 |
| Smoking status | 0.025 | 0.005 |
| Cycles completed | 0.025 | 0.044 |
| Genetic mutation | 0.024 | 0.023 |
| Tumour size | 0.023 | 0.038 |
| Age | 0.022 | 0.030 |
| Chemo regimen | 0.022 | 0.028 |
| BMI | 0.022 | 0.067 |
| Nausea severity | 0.018 | 0.010 |
| Sex | 0.016 | 0.004 |
| Neutropenia | 0.005 | 0.004 |
| Metastasis status | 0.001 | 0.002 |
| Overall survival months | **0.000** | 0.066 |

Two things to take from this. RF spreads its sensitivity more evenly and leans on
clinically sensible fields — dosage, cancer type, stage — where XGBoost leaned
hardest on BMI and survival months. And RF's 0.000 on survival months is the
leakage exclusion, confirmed end to end rather than assumed.

Metastasis moves the dashboard by 0.1 of a percentage point under RF, so anyone
testing by toggling that one field will think the app is broken. Stage I → IV
moves it 3.4 points. For a visible demo, vary dosage, cancer type and stage
together.

Across 300 randomly drawn patients: 0.436 to 0.607, median 0.531, 18 distinct
whole-percent values, all four classes predicted. Narrower than XGBoost's raw
range but distributed across classes instead of collapsing onto Partial — which
is the property that matters.

## 6. Open issues in the report

Flagging these because they are the kind of thing an examiner asks about.

**§3.2.1 describes a different study from the one Chapter 4 evaluated.** It lists
marital status, occupation, insurance and family support as features, and two
*binary* targets — completion (Completed / Not Completed) and response (Good /
Poor). The actual dataset and models use clinical features and one 4-class
`Tumor_Response`. Those two chapters need to be reconciled.

**No completion model exists.** Objective 1 (§1.3) promises models "for
predicting treatment completion and treatment response". All five trained models
predict response. The app's Completion card is therefore a rule-based estimate
with invented weights, labelled "estimate" in the UI and documented as carrying
no clinical validity. Either train the second model or drop the objective.

**Leakage is handled inconsistently across the five models.** Random Forest
excludes `Overall_Survival_Months`; XGBoost includes it, and leans on it as one of
its two strongest features. So Table 1 compares models trained on different
feature sets, which weakens it as a like-for-like benchmark — RF's 0.3082 was
earned on 14 features while XGBoost's 0.2173 had 15. Worth a sentence in the
report, and it strengthens rather than weakens the case for RF.

`Cycles_Completed` remains in all five, and is arguably leakage on the same
grounds: the stated purpose is prediction "before or during the early stages of
treatment", but how many cycles a patient completed is partly *is* the outcome.

**No model beats the majority-class baseline on accuracy.** Worth stating in the
report rather than leaving for a viva question. The honest framing is that the
dataset's features carry little signal for this target, which is a finding, not a
failure — but it should be named.

## 7. Verification performed

What was actually checked, so nobody has to re-derive it.

**Model loading** — all three files in `models/` load and score, each isolated in
a temp folder so discovery was unambiguous:

| File | Columns | Result |
| --- | --- | --- |
| `random_forest_model.pkl` | 14 | Stable, favourable 0.5273 |
| `model.pkl` | 15 | Partial, favourable 0.6025 |
| `xgb_Tumor_Response_model.json` | 15 | Partial, favourable 0.6025 |

The two XGBoost serializations agreeing to 4 decimal places here (and to 15 in
the earlier check) is what validates `features.py` — they are the same model saved
two ways, so a wrong encoding would make them diverge.

**Validation and error handling** — every rejection path returns a 422 naming the
field and what it expected, not a generic failure:

```
age below range    -> 422  age: Input should be greater than or equal to 30
bad cancer type    -> 422  cancerType='Pancreatic' is not a category the model was trained on...
bad stage          -> 422  tumorStage='V' is not a category...
bmi out of range   -> 422  bmi: Input should be less than or equal to 35
missing field      -> 422  bmi: Field required
non-numeric age    -> 422  age: Input should be a valid integer...
```

Confirmed in the browser too: injecting an invalid category past the dropdown
renders a red "Prediction failed" banner carrying the backend's message, keeps the
form values so nothing is retyped, and clears on the next valid submit. No
fabricated score is ever shown.

**Frontend** — production build succeeds (`vite build`, 1,583 modules, 170 kB JS /
54 kB gzipped). No console errors. Mobile at 375 px stacks to a single column with
the sidebar collapsing to a top bar. A varied patient (Leukemia, Stage IV, 600
mg/m²) returns 56% with a 20/24/32/24 breakdown against the baseline's 55% and
18/27/32/23, so the dashboard visibly tracks input.

## 8. Files changed

Backend, all rewritten:

- `features.py` — the §3.1.2 preprocessing contract; slug-based column matching;
  encodes a 16-column superset so a 14- or 15-column model both work
- `registry.py` — bundle unwrapping, RF-first discovery, native-booster adapter,
  and the `feature_names_in_` NumPy-truthiness fix described in §4
- `schemas.py` — documented ranges enforced as real constraints; nullable completion
- `main.py` — `ValueError` → 422, `ModelUnavailable` → 503
- `models/README.md` — load order, expected bundle format, preprocessing contract
- `make_dummy_models.py` — deleted (targeted the obsolete 11-column contract)

Frontend:

- `lib/fields.js` — rewritten; option strings are now the exact training
  categories, numeric bounds are the documented ranges, `default` seeds make the
  form submittable immediately
- `lib/predict.js` — rewritten; mock removed, error surfacing, risk bands,
  recommendation rules, the labelled completion estimate
- `components/ResultsDashboard.jsx` — rewritten; four-class breakdown, honest
  banner naming the serving model, "estimate" badge
- `components/PatientForm.jsx` — section icons rekeyed, renders section notes
- `components/Field.jsx` — stop the `default` seed leaking to the DOM

Docs: root `README.md` rewritten, `.claude/launch.json` added.

Dropdown values in `lib/fields.js` are training categories, not display labels.
Changing one means changing `backend/features.py` to match, or predictions get a
422.
